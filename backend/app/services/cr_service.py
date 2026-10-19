"""Class-representative operations: live status and operational rescheduling.

CRs act on the *live* version (active published, or the latest review version in
draft-preview mode). Changes are cohort-scoped for authorisation and **date-scoped**:
they are stored as a ``SessionOccurrence`` for one teaching week, never on the weekly
template row, so "not held" or a move this week does not leak into next week. Shared
cohorts see the change immediately because it hangs off the shared session. Every
mutation is audit-logged.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AdminRole,
    AdminUser,
    Cohort,
    CohortRepresentative,
    LiveStatus,
    SessionCohort,
    SessionOccurrence,
    TimetableSession,
    Venue,
    VenueNotice,
)
from app.core.campus import resolve_week
from app.services import occurrence_service as occ_svc
from app.services.audit_service import record as audit_record
from app.services.occurrence_service import Slot


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


def _slot_dict(slot: Slot) -> dict:
    return {
        "day_of_week": slot.day_of_week,
        "start_time": slot.start_time.isoformat(),
        "end_time": slot.end_time.isoformat(),
        "venue": slot.venue,
    }


def set_live_status(
    session: Session,
    *,
    user: AdminUser,
    session_id: uuid.UUID,
    status: LiveStatus,
    week: date | None = None,
    ip: str | None = None,
) -> tuple[TimetableSession, SessionOccurrence | None]:
    """Set the class's status for one teaching week (default: this week).

    Returns the template row and the week's occurrence (``None`` once the class is back
    to plain "scheduled" with no move).
    """
    row = get_authorized_session(session, user, session_id)
    wk = resolve_week(week)
    occ = occ_svc.get_or_create(session, row, wk)
    before = {"week": wk.isoformat(), "live_status": occ.live_status.value}
    now = datetime.now(timezone.utc)
    if status == LiveStatus.live:
        # Undoing "End class" resumes the class rather than restarting the clock.
        resume = occ.live_status == LiveStatus.ended and occ.live_started_at is not None
        if not resume:
            occ.live_started_at = now
        occ.live_ended_at = None
    elif status == LiveStatus.ended:
        if occ.live_started_at is None:
            occ.live_started_at = now
        occ.live_ended_at = now
    elif status == LiveStatus.not_held:
        occ.live_ended_at = now
    else:  # scheduled -> reset
        occ.live_started_at = None
        occ.live_ended_at = None
    occ.live_status = status
    occ.updated_by = user.id
    kept = not occ_svc.prune(session, occ)
    session.flush()
    audit_record(session, actor=user, action="cr.live_status", entity_type="timetable_session",
                 entity_id=str(row.id), before=before,
                 after={"week": wk.isoformat(), "live_status": status.value}, ip=ip)
    return row, occ if kept else None


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
    week: date | None = None,
    ip: str | None = None,
) -> tuple[TimetableSession, SessionOccurrence | None]:
    """Move one week's class to another day/time/venue of the same week.

    ``venue=None`` keeps the current venue; ``venue=""`` clears it. Moving a class back
    to its published slot removes the move.
    """
    if end_time <= start_time:
        raise CrError("End time must be after start time.")
    if day_of_week is not None and not 1 <= day_of_week <= 7:
        raise CrError("Day of week must be 1-7.")
    row = get_authorized_session(session, user, session_id)
    wk = resolve_week(week)
    occ = occ_svc.get_or_create(session, row, wk)
    current = occ_svc.effective_slot(row, occ)
    target = Slot(
        day_of_week if day_of_week is not None else current.day_of_week,
        start_time,
        end_time,
        current.venue if venue is None else (venue.strip() or None),
    )
    occ_svc.set_move(occ, row, target, reason)
    occ.updated_by = user.id
    kept = not occ_svc.prune(session, occ)
    session.flush()
    audit_record(session, actor=user, action="cr.reschedule", entity_type="timetable_session",
                 entity_id=str(row.id),
                 before={"week": wk.isoformat(), **_slot_dict(current)},
                 after={"week": wk.isoformat(), **_slot_dict(target), "reason": reason}, ip=ip)
    return row, occ if kept else None


def swap_sessions(
    session: Session,
    *,
    user: AdminUser,
    session_id: uuid.UUID,
    with_session_id: uuid.UUID,
    reason: str | None = None,
    week: date | None = None,
    ip: str | None = None,
) -> list[tuple[TimetableSession, SessionOccurrence | None]]:
    """Exchange the slots (day, time, venue) of two classes for one week.

    Both sessions must belong to one of the class representative's cohorts. The
    published slots are untouched, so students see "moved from ..." for that week only.
    """
    if session_id == with_session_id:
        raise CrError("Pick two different classes to swap.")
    a = get_authorized_session(session, user, session_id)
    b = get_authorized_session(session, user, with_session_id)
    wk = resolve_week(week)
    occ_a = occ_svc.get_or_create(session, a, wk)
    occ_b = occ_svc.get_or_create(session, b, wk)
    slot_a = occ_svc.effective_slot(a, occ_a)
    slot_b = occ_svc.effective_slot(b, occ_b)
    occ_svc.set_move(occ_a, a, slot_b, reason)
    occ_svc.set_move(occ_b, b, slot_a, reason)
    occ_a.updated_by = occ_b.updated_by = user.id
    kept_a = not occ_svc.prune(session, occ_a)
    kept_b = not occ_svc.prune(session, occ_b)
    session.flush()
    audit_record(session, actor=user, action="cr.swap", entity_type="timetable_session",
                 entity_id=str(a.id),
                 before={"week": wk.isoformat(),
                         "a": {"id": str(a.id), **_slot_dict(slot_a)},
                         "b": {"id": str(b.id), **_slot_dict(slot_b)}},
                 after={"week": wk.isoformat(),
                        "a": {"id": str(a.id), **_slot_dict(slot_b)},
                        "b": {"id": str(b.id), **_slot_dict(slot_a)}},
                 ip=ip)
    return [(a, occ_a if kept_a else None), (b, occ_b if kept_b else None)]


def institute_sessions(
    session: Session, user: AdminUser, *, version, week: date, day: int | None = None,
) -> tuple[list[TimetableSession], dict[uuid.UUID, SessionOccurrence]]:
    """All sessions in the live version as they happen in ``week`` (optionally one day)."""
    rows = list(session.execute(
        select(TimetableSession).where(TimetableSession.version_id == version.id)
    ).scalars().all())
    occurrences = occ_svc.load_occurrences(session, [r.id for r in rows], week)
    if day is not None:
        rows = [r for r in rows if occ_svc.effective_slot(r, occurrences.get(r.id)).day_of_week == day]
    return occ_svc.sorted_by_effective(rows, occurrences), occurrences


def room_availability(
    session: Session, user: AdminUser, *, version, day: int, start_time: time, end_time: time,
    week: date | None = None,
) -> list[dict]:
    """Venues and whether they are free during [start_time, end_time) on ``day``.

    Uses this week's effective timetable: a class moved elsewhere frees its room, a class
    marked "not held" frees its room, and a class moved in occupies the new one. Active
    venue notices for the week also block a venue so it is not taken by mistake.
    """
    wk = resolve_week(week)
    venues = session.execute(select(Venue).order_by(Venue.code)).scalars().all()
    rows, occurrences = institute_sessions(session, user, version=version, week=wk, day=day)
    busy_codes: set[str] = set()
    busy_ids: set[uuid.UUID] = set()
    for row in rows:
        occ = occurrences.get(row.id)
        if occ_svc.live_status(occ) == LiveStatus.not_held:
            continue
        slot = occ_svc.effective_slot(row, occ)
        if not (slot.start_time < end_time and slot.end_time > start_time):
            continue
        if occ_svc.is_moved(occ):
            if slot.venue:
                busy_codes.add(slot.venue)
        elif row.venue_id is not None:
            busy_ids.add(row.venue_id)
        elif slot.venue:
            busy_codes.add(slot.venue)
    notices = {
        n.venue: n
        for n in session.execute(
            select(VenueNotice).where(
                VenueNotice.cleared_at.is_(None),
                VenueNotice.week_start == wk,
                VenueNotice.day_of_week == day,
            )
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
        occupied = v.id in busy_ids or v.code in busy_codes
        result.append({
            "venue": v.code,
            "name": v.name,
            "free": not occupied and not notice_overlaps,
            "notice": _notice_dict(notice) if notice else None,
        })
    return result


# --- venue notices (heads-up that a venue is/will be occupied) -------------

def _notice_dict(n: VenueNotice, cohort_code: str | None = None) -> dict:
    return {
        "id": str(n.id),
        "venue": n.venue,
        "cohort_code": cohort_code,
        "week_start": n.week_start.isoformat(),
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
    week: date | None = None,
    ip: str | None = None,
) -> VenueNotice:
    venue = venue.strip()
    if not venue:
        raise CrError("Venue is required.")
    if end_time is not None and end_time <= start_time:
        raise CrError("End time must be after start time.")
    wk = resolve_week(week)
    notice = VenueNotice(
        venue=venue,
        week_start=wk,
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
                 after={"venue": venue, "week": wk.isoformat(), "day": day_of_week,
                        "start": start_time.isoformat(),
                        "end": end_time.isoformat() if end_time else None},
                 ip=ip)
    return notice


def list_venue_notices(
    session: Session, *, day: int | None = None, week: date | None = None,
    include_cleared: bool = False,
):
    """Heads-ups for one teaching week (default: this week)."""
    stmt = select(VenueNotice, Cohort.code).outerjoin(
        Cohort, Cohort.id == VenueNotice.cohort_id
    ).where(VenueNotice.week_start == resolve_week(week))
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
