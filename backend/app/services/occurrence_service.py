"""Per-week view of the timetable: the published template plus class-rep overrides.

A ``TimetableSession`` is the weekly slot from the PDF. A ``SessionOccurrence`` records
what is different about it in one teaching week (live status, or a move within that
week). These helpers load the overrides for a week and resolve each session's
*effective* slot for that week, so every reader (public timetable, CR views, room
availability, calendar export) agrees.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.campus import current_week_start
from app.models import (
    Cohort,
    LiveStatus,
    SessionCohort,
    SessionOccurrence,
    TimetableSession,
)


@dataclass(frozen=True)
class Slot:
    day_of_week: int
    start_time: time
    end_time: time
    venue: str | None


def template_slot(row: TimetableSession) -> Slot:
    return Slot(row.day_of_week, row.start_time, row.end_time, row.venue_raw)


def is_moved(occ: SessionOccurrence | None) -> bool:
    return occ is not None and occ.moved_start_time is not None


def effective_slot(row: TimetableSession, occ: SessionOccurrence | None) -> Slot:
    if is_moved(occ):
        return Slot(occ.moved_day_of_week or row.day_of_week, occ.moved_start_time,
                    occ.moved_end_time or row.end_time, occ.moved_venue_raw)
    return template_slot(row)


def live_status(occ: SessionOccurrence | None) -> LiveStatus:
    return occ.live_status if occ is not None else LiveStatus.scheduled


def load_occurrences(
    db: Session, session_ids: list[uuid.UUID], week: date
) -> dict[uuid.UUID, SessionOccurrence]:
    if not session_ids:
        return {}
    rows = db.execute(
        select(SessionOccurrence).where(
            SessionOccurrence.session_id.in_(session_ids),
            SessionOccurrence.week_start == week,
        )
    ).scalars()
    return {o.session_id: o for o in rows}


def get_or_create(db: Session, row: TimetableSession, week: date) -> SessionOccurrence:
    occ = db.execute(
        select(SessionOccurrence).where(
            SessionOccurrence.session_id == row.id, SessionOccurrence.week_start == week
        )
    ).scalar_one_or_none()
    if occ is None:
        occ = SessionOccurrence(session_id=row.id, week_start=week, live_status=LiveStatus.scheduled)
        db.add(occ)
    return occ


def set_move(occ: SessionOccurrence, row: TimetableSession, target: Slot, reason: str | None) -> None:
    """Move this week's occurrence to ``target``; moving it back to the template clears it."""
    if target == template_slot(row):
        occ.moved_day_of_week = None
        occ.moved_start_time = None
        occ.moved_end_time = None
        occ.moved_venue_raw = None
        occ.moved_at = None
        occ.reason = None
    else:
        occ.moved_day_of_week = target.day_of_week
        occ.moved_start_time = target.start_time
        occ.moved_end_time = target.end_time
        occ.moved_venue_raw = target.venue
        occ.moved_at = datetime.now(timezone.utc)
        if reason is not None:
            occ.reason = reason


def prune(db: Session, occ: SessionOccurrence) -> bool:
    """Drop an override that no longer changes anything. Returns True if deleted."""
    if occ.live_status == LiveStatus.scheduled and not is_moved(occ):
        if occ in db.new:
            db.expunge(occ)
        else:
            db.delete(occ)
        return True
    return False


def sorted_by_effective(
    rows: list[TimetableSession], occurrences: dict[uuid.UUID, SessionOccurrence]
) -> list[TimetableSession]:
    def key(r: TimetableSession):
        slot = effective_slot(r, occurrences.get(r.id))
        return (slot.day_of_week, slot.start_time, slot.venue or "")

    return sorted(rows, key=key)


def carry_forward(db: Session, from_version_id, to_version_id) -> int:
    """Copy this and future weeks' overrides onto the matching sessions of another version.

    Used when a new version is published (or rolled back to), so class-rep changes for
    the current week survive. Sessions match on course, published slot and cohorts.
    Returns the number of overrides copied.
    """
    if from_version_id is None or from_version_id == to_version_id:
        return 0
    week = current_week_start()
    pending = db.execute(
        select(SessionOccurrence, TimetableSession)
        .join(TimetableSession, TimetableSession.id == SessionOccurrence.session_id)
        .where(TimetableSession.version_id == from_version_id, SessionOccurrence.week_start >= week)
    ).all()
    if not pending:
        return 0

    def cohorts_of(version_id) -> dict[uuid.UUID, frozenset[str]]:
        out: dict[uuid.UUID, set[str]] = {}
        for sid, code in db.execute(
            select(SessionCohort.session_id, Cohort.code)
            .join(Cohort, Cohort.id == SessionCohort.cohort_id)
            .join(TimetableSession, TimetableSession.id == SessionCohort.session_id)
            .where(TimetableSession.version_id == version_id)
        ).all():
            out.setdefault(sid, set()).add(code)
        return {k: frozenset(v) for k, v in out.items()}

    def match_key(row: TimetableSession, cohorts: frozenset[str]):
        return (row.course_code_raw or row.course_name_raw, row.day_of_week, row.start_time, cohorts)

    old_cohorts = cohorts_of(from_version_id)
    new_cohorts = cohorts_of(to_version_id)
    targets = {
        match_key(r, new_cohorts.get(r.id, frozenset())): r
        for r in db.execute(
            select(TimetableSession).where(TimetableSession.version_id == to_version_id)
        ).scalars()
    }
    copied = 0
    for occ, row in pending:
        target = targets.get(match_key(row, old_cohorts.get(row.id, frozenset())))
        if target is None:
            continue
        existing = db.execute(
            select(SessionOccurrence).where(
                SessionOccurrence.session_id == target.id,
                SessionOccurrence.week_start == occ.week_start,
            )
        ).scalar_one_or_none()
        if existing is not None:
            continue
        db.add(SessionOccurrence(
            session_id=target.id, week_start=occ.week_start, live_status=occ.live_status,
            live_started_at=occ.live_started_at, live_ended_at=occ.live_ended_at,
            moved_day_of_week=occ.moved_day_of_week, moved_start_time=occ.moved_start_time,
            moved_end_time=occ.moved_end_time, moved_venue_raw=occ.moved_venue_raw,
            moved_at=occ.moved_at, reason=occ.reason, updated_by=occ.updated_by,
        ))
        copied += 1
    db.flush()
    return copied
