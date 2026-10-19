"""Shared serializer for timetable sessions used by the public and CR APIs."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Cohort, Course, SessionCohort, SessionLecturer, TimetableSession


def _time_str(t) -> str | None:
    return t.isoformat() if t is not None else None


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
) -> dict:
    cohorts = cohorts or []
    shared_with = sorted(c for c in cohorts if c != base_cohort_code) if base_cohort_code else sorted(cohorts)
    return {
        "id": str(s.id),
        "day_of_week": s.day_of_week,
        "start_time": _time_str(s.start_time),
        "end_time": _time_str(s.end_time),
        "course_code": s.course_code_raw,
        "course_name": s.course_name_raw,
        "department": course.department if course else None,
        "lecturers": sorted(lecturers or []),
        "venue": s.venue_raw,
        "session_type": s.session_type.value if s.session_type else None,
        "shared_with": shared_with,
        "cohorts": sorted(cohorts),
        "source_page": s.source_page,
        "live_status": s.live_status.value,
        "live_started_at": s.live_started_at.isoformat() if s.live_started_at else None,
        "live_ended_at": s.live_ended_at.isoformat() if s.live_ended_at else None,
        "rescheduled": s.rescheduled_at is not None,
        "reschedule_reason": s.reschedule_reason,
        "rescheduled_at": s.rescheduled_at.isoformat() if s.rescheduled_at else None,
        "original_day_of_week": s.original_day_of_week,
        "original_start_time": _time_str(s.original_start_time),
        "original_end_time": _time_str(s.original_end_time),
        "original_venue": s.original_venue_raw,
    }
