"""Class-representative operations: live status and operational rescheduling.

CRs act on the *live* version (active published, or the latest review version in
draft-preview mode). Changes are cohort-scoped for authorisation but applied to the
session row itself, so shared cohorts see the change immediately. Every mutation is
audit-logged.
"""
from __future__ import annotations

import uuid
from datetime import datetime, time, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AdminRole,
    AdminUser,
    Cohort,
    CohortRepresentative,
    LiveStatus,
    SessionCohort,
    TimetableSession,
    Venue,
    VenueNotice,
)
from app.services.audit_service import record as audit_record


class CrError(Exception):
    pass


def create_cr(
    session: Session,
    *,
    email: str,
    password: str,
    cohort_codes: list[str],
    display_name: str | None = None,
) -> AdminUser:
    """Create a class-representative account linked to one or more cohorts."""
    from app.services.auth_service import create_admin

    codes = [c.strip().upper() for c in cohort_codes if c.strip()]
    if not codes:
        raise CrError("At least one cohort code is required.")
    cohorts = session.execute(select(Cohort).where(Cohort.code.in_(codes))).scalars().all()
    found = {c.code for c in cohorts}
    missing = [c for c in codes if c not in found]
    if missing:
        raise CrError(f"Unknown cohort(s): {', '.join(missing)}")
    user = create_admin(session, email, password, role=AdminRole.cr, display_name=display_name)
    for cohort in cohorts:
        session.add(CohortRepresentative(user_id=user.id, cohort_id=cohort.id))
    session.flush()
    return user


def cr_cohorts(session: Session, user: AdminUser) -> list[Cohort]:
    return session.execute(
        select(Cohort)
        .join(CohortRepresentative, CohortRepresentative.cohort_id == Cohort.id)
        .where(CohortRepresentative.user_id == user.id)
        .order_by(Cohort.code)
    ).scalars().all()


def _unauthorized() -> CrError:
    return CrError("Session is not in one of your cohorts.")


def get_authorized_session(session: Session, user: AdminUser, session_id: uuid.UUID) -> TimetableSession:
    cohort_ids = [c.id for c in cr_cohorts(session, user)]
    row = session.get(TimetableSession, session_id)
    if row is None:
        raise CrError("Session not found.")
    if not cohort_ids:
        raise _unauthorized()
    linked = session.execute(
        select(SessionCohort.cohort_id).where(
            SessionCohort.session_id == session_id,
            SessionCohort.cohort_id.in_(cohort_ids),
        )
    ).first()
    if linked is None:
        raise _unauthorized()
    return row


def _audit_live(session: Session, user: AdminUser, row: TimetableSession, before, after, ip):
    audit_record(session, actor=user, action="cr.live_status", entity_type="timetable_session",
                 entity_id=str(row.id), before=before, after=after, ip=ip)


def set_live_status(
    session: Session,
    *,
    user: AdminUser,
    session_id: uuid.UUID,
    status: LiveStatus,
    ip: str | None = None,
) -> TimetableSession:
    row = get_authorized_session(session, user, session_id)
    before = {"live_status": row.live_status.value}
    now = datetime.now(timezone.utc)
    if status == LiveStatus.live:
        row.live_status = LiveStatus.live
        row.live_started_at = now
        row.live_ended_at = None
    elif status == LiveStatus.ended:
        row.live_status = LiveStatus.ended
        if row.live_started_at is None:
            row.live_started_at = now
        row.live_ended_at = now
    elif status == LiveStatus.not_held:
        row.live_status = LiveStatus.not_held
        row.live_ended_at = now
    else:  # scheduled -> reset
        row.live_status = LiveStatus.scheduled
        row.live_started_at = None
        row.live_ended_at = None
    session.flush()
    _audit_live(session, user, row, before, {"live_status": row.live_status.value}, ip)
    return row


def reschedule_session(
    session: Session,
    *,
    user: AdminUser,
    session_id: uuid.UUID,
    start_time: time,
    end_time: time,
    day_of_week: int | None = None,
    venue: str | None = None,
    reason: str | None = None,
    ip: str | None = None,
) -> TimetableSession:
    if end_time <= start_time:
        raise CrError("End time must be after start time.")
    if day_of_week is not None and not 1 <= day_of_week <= 7:
        raise CrError("Day of week must be 1-7.")
    row = get_authorized_session(session, user, session_id)
    before = _slot_snapshot(row)
    _capture_originals(row)
    if day_of_week is not None:
        row.day_of_week = day_of_week
    row.start_time = start_time
    row.end_time = end_time
    if venue is not None:
        row.venue_raw = venue or None
    row.reschedule_reason = reason
    _settle_reschedule(row)
    session.flush()
    audit_record(session, actor=user, action="cr.reschedule", entity_type="timetable_session",
                 entity_id=str(row.id), before=before, after=_slot_snapshot(row), ip=ip)
    return row


# --- operational slot changes: move across days and swap -------------------

def _slot_snapshot(row: TimetableSession) -> dict:
    return {
        "day_of_week": row.day_of_week,
        "start_time": row.start_time.isoformat(),
        "end_time": row.end_time.isoformat(),
        "venue": row.venue_raw,
    }


def _capture_originals(row: TimetableSession) -> None:
    """Remember the published slot the first time a session is changed."""
    if row.rescheduled_at is None:
        row.original_day_of_week = row.day_of_week
        row.original_start_time = row.start_time
        row.original_end_time = row.end_time
        row.original_venue_raw = row.venue_raw


def _settle_reschedule(row: TimetableSession) -> None:
    """Mark the row as rescheduled, or clear it if it is back to its original slot."""
    unchanged = (
        row.original_day_of_week == row.day_of_week
        and row.original_start_time == row.start_time
        and row.original_end_time == row.end_time
        and (row.original_venue_raw or None) == (row.venue_raw or None)
    )
    if unchanged:
        row.rescheduled_at = None
        row.reschedule_reason = None
        row.original_day_of_week = None
        row.original_start_time = None
        row.original_end_time = None
        row.original_venue_raw = None
    else:
        row.rescheduled_at = datetime.now(timezone.utc)


def swap_sessions(
    session: Session,
    *,
    user: AdminUser,
    session_id: uuid.UUID,
    with_session_id: uuid.UUID,
    reason: str | None = None,
    ip: str | None = None,
) -> tuple[TimetableSession, TimetableSession]:
    """Exchange the whole slot (day, time, venue) of two sessions.

    Both sessions must belong to one of the class representative's cohorts. Original
    slots are preserved so students can see "moved from ...".
    """
    if session_id == with_session_id:
        raise CrError("Pick two different classes to swap.")
    a = get_authorized_session(session, user, session_id)
    b = get_authorized_session(session, user, with_session_id)
    before = {"a": {"id": str(a.id), **_slot_snapshot(a)}, "b": {"id": str(b.id), **_slot_snapshot(b)}}
    _capture_originals(a)
    _capture_originals(b)
    a.day_of_week, b.day_of_week = b.day_of_week, a.day_of_week
    a.start_time, b.start_time = b.start_time, a.start_time
    a.end_time, b.end_time = b.end_time, a.end_time
    a.venue_id, b.venue_id = b.venue_id, a.venue_id
    a.venue_raw, b.venue_raw = b.venue_raw, a.venue_raw
    if reason is not None:
        a.reschedule_reason = reason
        b.reschedule_reason = reason
    _settle_reschedule(a)
    _settle_reschedule(b)
    session.flush()
    audit_record(session, actor=user, action="cr.swap", entity_type="timetable_session",
                 entity_id=str(a.id),
                 before=before,
                 after={"a": {"id": str(a.id), **_slot_snapshot(a)},
                        "b": {"id": str(b.id), **_slot_snapshot(b)}},
                 ip=ip)
    return a, b


def institute_sessions(
    session: Session, user: AdminUser, *, version, day: int | None = None, limit: int = 1000
) -> list[TimetableSession]:
    """All sessions in the live version (for finding free rooms / open slots)."""
    stmt = select(TimetableSession).where(TimetableSession.version_id == version.id)
    if day is not None:
        stmt = stmt.where(TimetableSession.day_of_week == day)
    stmt = stmt.order_by(
        TimetableSession.day_of_week, TimetableSession.start_time, TimetableSession.venue_raw
    ).limit(limit)
    return list(session.execute(stmt).scalars().all())


def room_availability(
    session: Session, user: AdminUser, *, version, day: int, start_time: time, end_time: time
) -> list[dict]:
    """Venues and whether they are free during [start_time, end_time) on ``day``.

    Also surfaces active venue notices so a venue about to be occupied is not taken
    by mistake.
    """
    venues = session.execute(select(Venue).order_by(Venue.code)).scalars().all()
    busy_ids = {
        vid
        for (vid,) in session.execute(
            select(TimetableSession.venue_id).where(
                TimetableSession.version_id == version.id,
                TimetableSession.day_of_week == day,
                TimetableSession.venue_id.is_not(None),
                TimetableSession.start_time < end_time,
                TimetableSession.end_time > start_time,
            )
        ).all()
    }
    notices = {
        n.venue: n
        for n in session.execute(
            select(VenueNotice).where(VenueNotice.cleared_at.is_(None), VenueNotice.day_of_week == day)
        ).scalars()
    }
    result = []
    for v in venues:
        notice = notices.get(v.code)
        notice_overlaps = bool(
            notice
            and notice.start_time < end_time
            and (notice.end_time is None or notice.end_time > start_time)
        )
        result.append({
            "venue": v.code,
            "name": v.name,
            "free": v.id not in busy_ids and not notice_overlaps,
            "notice": _notice_dict(notice) if notice else None,
        })
    return result


# --- venue notices (heads-up that a venue is/will be occupied) -------------

def _notice_dict(n: VenueNotice, cohort_code: str | None = None) -> dict:
    return {
        "id": str(n.id),
        "venue": n.venue,
        "cohort_code": cohort_code,
        "day_of_week": n.day_of_week,
        "start_time": n.start_time.isoformat(),
        "end_time": n.end_time.isoformat() if n.end_time else None,
        "note": n.note,
        "created_at": n.updated_at.isoformat() if n.updated_at else None,
    }


def create_venue_notice(
    session: Session,
    *,
    user: AdminUser,
    venue: str,
    day_of_week: int,
    start_time: time,
    end_time: time | None = None,
    note: str | None = None,
    ip: str | None = None,
) -> VenueNotice:
    venue = venue.strip()
    if not venue:
        raise CrError("Venue is required.")
    if end_time is not None and end_time <= start_time:
        raise CrError("End time must be after start time.")
    notice = VenueNotice(
        venue=venue,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        note=note,
        created_by=user.id,
    )
    cohorts = cr_cohorts(session, user)
    if cohorts:
        notice.cohort_id = cohorts[0].id
    session.add(notice)
    session.flush()
    audit_record(session, actor=user, action="cr.venue_notice", entity_type="venue_notice",
                 entity_id=str(notice.id),
                 after={"venue": venue, "day": day_of_week,
                        "start": start_time.isoformat(),
                        "end": end_time.isoformat() if end_time else None},
                 ip=ip)
    return notice


def list_venue_notices(session: Session, *, day: int | None = None, include_cleared: bool = False):
    stmt = select(VenueNotice, Cohort.code).outerjoin(
        Cohort, Cohort.id == VenueNotice.cohort_id
    )
    if not include_cleared:
        stmt = stmt.where(VenueNotice.cleared_at.is_(None))
    if day is not None:
        stmt = stmt.where(VenueNotice.day_of_week == day)
    stmt = stmt.order_by(VenueNotice.day_of_week, VenueNotice.start_time)
    return [_notice_dict(n, code) for n, code in session.execute(stmt).all()]


def clear_venue_notice(
    session: Session, *, user: AdminUser, notice_id: uuid.UUID, ip: str | None = None
) -> VenueNotice:
    notice = session.get(VenueNotice, notice_id)
    if notice is None:
        raise CrError("Venue notice not found.")
    if notice.cleared_at is None:
        notice.cleared_at = datetime.now(timezone.utc)
        session.flush()
        audit_record(session, actor=user, action="cr.venue_notice_clear", entity_type="venue_notice",
                     entity_id=str(notice.id), after={"venue": notice.venue}, ip=ip)
    return notice
