"""Shared serializer for timetable sessions used by the public and CR APIs."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Cohort,
    Course,
    SessionCohort,
    SessionLecturer,
    SessionOccurrence,
    TimetableSession,
)
from app.services.occurrence_service import effective_slot, is_moved, live_status


def _time_str(t) -> str | None:
    return t.isoformat() if t is not None else None


def _utc_str(dt: datetime | None) -> str | None:
    """ISO timestamp with an explicit UTC offset (SQLite hands back naive UTC values)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def collect_details(db: Session, sessions: list[TimetableSession]):
    """Return ``(cohort_map, lecturer_map, course_map)`` for the given sessions."""
    session_ids = [s.id for s in sessions]
    cohort_map: dict[uuid.UUID, list[str]] = {}
    lecturer_map: dict[uuid.UUID, list[str]] = {}
    if session_ids:
        for sid, code in db.execute(
            select(SessionCohort.session_id, Cohort.code)
            .join(Cohort, Cohort.id == SessionCohort.cohort_id)
            .where(SessionCohort.session_id.in_(session_ids))
        ).all():
            cohort_map.setdefault(sid, []).append(code)
        for sid, name in db.execute(
            select(SessionLecturer.session_id, SessionLecturer.raw_name)
            .where(SessionLecturer.session_id.in_(session_ids))
        ).all():
            lecturer_map.setdefault(sid, []).append(name)
    course_ids = [s.course_id for s in sessions if s.course_id]
    course_map: dict[uuid.UUID, Course] = {}
    if course_ids:
        course_map = {
            c.id: c
            for c in db.execute(select(Course).where(Course.id.in_(course_ids))).scalars()
        }
    return cohort_map, lecturer_map, course_map


def session_to_dict(
    s: TimetableSession,
    *,
    course: Course | None = None,
    cohorts: list[str] | None = None,
    lecturers: list[str] | None = None,
    base_cohort_code: str | None = None,
    occurrence: SessionOccurrence | None = None,
) -> dict:
    """Serialize a session as it happens in one week (template + that week's override)."""
    cohorts = cohorts or []
    shared_with = sorted(c for c in cohorts if c != base_cohort_code) if base_cohort_code else sorted(cohorts)
    slot = effective_slot(s, occurrence)
    moved = is_moved(occurrence)
    occ = occurrence
    return {
        "id": str(s.id),
        "day_of_week": slot.day_of_week,
        "start_time": _time_str(slot.start_time),
        "end_time": _time_str(slot.end_time),
        "course_code": s.course_code_raw,
        "course_name": s.course_name_raw,
        "department": course.department if course else None,
        "lecturers": sorted(lecturers or []),
        "venue": slot.venue,
        "session_type": s.session_type.value if s.session_type else None,
        "shared_with": shared_with,
        "cohorts": sorted(cohorts),
        "source_page": s.source_page,
        "live_status": live_status(occ).value,
        "live_started_at": _utc_str(occ.live_started_at) if occ else None,
        "live_ended_at": _utc_str(occ.live_ended_at) if occ else None,
        "rescheduled": moved,
        "reschedule_reason": occ.reason if moved else None,
        "rescheduled_at": _utc_str(occ.moved_at) if moved else None,
        "original_day_of_week": s.day_of_week if moved else None,
        "original_start_time": _time_str(s.start_time) if moved else None,
        "original_end_time": _time_str(s.end_time) if moved else None,
        "original_venue": s.venue_raw if moved else None,
    }


def serialize_for_week(
    db: Session,
    rows: list[TimetableSession],
    week,
    *,
    base_cohort_code: str | None = None,
    occurrences: dict | None = None,
) -> list[dict]:
    """Serialize sessions as they happen in ``week`` (Monday), ordered by effective slot."""
    from app.services.occurrence_service import load_occurrences, sorted_by_effective

    if occurrences is None:
        occurrences = load_occurrences(db, [r.id for r in rows], week)
    rows = sorted_by_effective(list(rows), occurrences)
    cohort_map, lecturer_map, course_map = collect_details(db, rows)
    return [
        session_to_dict(
            r,
            course=course_map.get(r.course_id),
            cohorts=cohort_map.get(r.id, []),
            lecturers=lecturer_map.get(r.id, []),
            base_cohort_code=base_cohort_code,
            occurrence=occurrences.get(r.id),
        )
        for r in rows
    ]
