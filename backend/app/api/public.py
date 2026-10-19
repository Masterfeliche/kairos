"""Public read-only API: published, active-version data (docs/05 §6.5).

Also exposes an optional *draft preview* (latest `review` version) that is only
available when ``TT_ALLOW_DRAFT_PREVIEW=true`` — a dev/staging aid so the student
site can be exercised before a version clears the publish gate. Never enable in
production.
"""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.campus import resolve_week
from app.core.db import get_session
from app.models import (
    AcademicPeriod,
    Cohort,
    Programme,
    SessionCohort,
    SessionOccurrence,
    SourceDocument,
    TimetableSession,
    TimetableVersion,
)
from app.services.calendar_service import generate_cohort_ics
from app.services.occurrence_service import effective_slot, is_moved, live_status
from app.services.session_view import collect_details, serialize_for_week, session_to_dict
from app.services.version_service import preview_allowed, resolve_live_version

router = APIRouter(prefix="/api/v1", tags=["public"])


def _version_out(db: Session, version: TimetableVersion, *, preview: bool) -> dict:
    source = db.get(SourceDocument, version.source_document_id)
    return {
        "id": str(version.id),
        "period_id": str(version.period_id),
        "label": version.label,
        "status": version.status.value,
        "is_active": version.is_active,
        "is_preview": preview,
        "published_at": version.published_at.isoformat() if version.published_at else None,
        "updated_at": version.updated_at.isoformat() if version.updated_at else None,
        "source_filename": source.original_filename if source else None,
    }


def _preview_requested(preview: bool) -> bool:
    return preview_allowed(preview)


@router.get("/periods")
def list_periods(db: Session = Depends(get_session)):
    rows = db.execute(select(AcademicPeriod).order_by(AcademicPeriod.year_label.desc())).scalars()
    return [
        {"id": str(p.id), "year_label": p.year_label, "semester": p.semester.value,
         "is_active": p.is_active}
        for p in rows
    ]


@router.get("/programmes")
def list_programmes(db: Session = Depends(get_session)):
    """Programmes with their cohorts, grouped for the selection screen."""
    rows = db.execute(
        select(Programme, Cohort)
        .outerjoin(Cohort, Cohort.programme_id == Programme.id)
        .order_by(Programme.level, Programme.name, Cohort.code)
    ).all()
    grouped: dict[str, dict] = {}
    for programme, cohort in rows:
        entry = grouped.setdefault(str(programme.id), {
            "id": str(programme.id),
            "name": programme.name,
            "code": programme.code,
            "level": programme.level.value,
            "department": programme.department,
            "cohorts": [],
        })
        if cohort is not None:
            entry["cohorts"].append({
                "id": str(cohort.id),
                "code": cohort.code,
                "intake_year": cohort.intake_year,
                "section": cohort.section,
            })
    return list(grouped.values())


@router.get("/cohorts")
def list_cohorts(db: Session = Depends(get_session)):
    rows = db.execute(select(Cohort).order_by(Cohort.code)).scalars()
    return [{"id": str(c.id), "code": c.code, "intake_year": c.intake_year,
             "section": c.section} for c in rows]


@router.get("/venue-notices")
def venue_notices(
    day: int | None = Query(None, ge=1, le=7),
    week: date | None = Query(None, description="Any date in the teaching week (default: this week)"),
    db: Session = Depends(get_session),
):
    """Active venue heads-ups for one week so students know when to leave a venue."""
    from app.services.cr_service import list_venue_notices

    return {"notices": list_venue_notices(db, day=day, week=week)}


@router.get("/versions/active")
def active_version(preview: bool = Query(False), db: Session = Depends(get_session)):
    _preview_requested(preview)
    resolved = resolve_live_version(db, preview=preview)
    if resolved is None:
        raise HTTPException(status_code=404, detail="No published version.")
    version, is_preview = resolved
    return _version_out(db, version, preview=is_preview)


@router.get("/timetable")
def timetable(
    cohort_code: str,
    week: date | None = Query(None, description="Any date in the teaching week (default: this week)"),
    preview: bool = Query(False),
    db: Session = Depends(get_session),
):
    """A cohort's timetable as it happens in one teaching week (published slots plus
    that week's class-rep changes)."""
    _preview_requested(preview)
    cohort = db.execute(
        select(Cohort).where(Cohort.code == cohort_code.upper())
    ).scalar_one_or_none()
    if cohort is None:
        raise HTTPException(status_code=404, detail="Unknown cohort.")

    resolved = resolve_live_version(db, preview=preview)
    if resolved is None:
        raise HTTPException(status_code=404, detail="No published version.")
    version, is_preview = resolved

    sessions = db.execute(
        select(TimetableSession)
        .join(SessionCohort, SessionCohort.session_id == TimetableSession.id)
        .where(
            SessionCohort.cohort_id == cohort.id,
            TimetableSession.version_id == version.id,
        )
        .order_by(TimetableSession.day_of_week, TimetableSession.start_time)
    ).scalars().all()

    wk = resolve_week(week)
    items = serialize_for_week(db, sessions, wk, base_cohort_code=cohort.code)

    return {
        "cohort": {"id": str(cohort.id), "code": cohort.code,
                   "intake_year": cohort.intake_year, "section": cohort.section},
        "version": _version_out(db, version, preview=is_preview),
        "week_start": wk.isoformat(),
        "sessions": items,
    }


@router.get("/timetable/export.ics")
def export_timetable_ics(
    cohort_code: str,
    preview: bool = Query(False),
    db: Session = Depends(get_session),
):
    """Export cohort timetable as an RFC 5545 iCalendar (.ics) file."""
    _preview_requested(preview)
    cohort = db.execute(
        select(Cohort).where(Cohort.code == cohort_code.upper())
    ).scalar_one_or_none()
    if cohort is None:
        raise HTTPException(status_code=404, detail="Unknown cohort.")

    resolved = resolve_live_version(db, preview=preview)
    if resolved is None:
        raise HTTPException(status_code=404, detail="No published version.")
    version, is_preview = resolved

    sessions = db.execute(
        select(TimetableSession)
        .join(SessionCohort, SessionCohort.session_id == TimetableSession.id)
        .where(
            SessionCohort.cohort_id == cohort.id,
            TimetableSession.version_id == version.id,
        )
        .order_by(TimetableSession.day_of_week, TimetableSession.start_time)
    ).scalars().all()

    cohort_map, lecturer_map, course_map = collect_details(db, sessions)
    items = [
        session_to_dict(
            s,
            course=course_map.get(s.course_id),
            cohorts=cohort_map.get(s.id, []),
            lecturers=lecturer_map.get(s.id, []),
            base_cohort_code=cohort.code,
        )
        for s in sessions
    ]

    first_week = resolve_week(None)
    weeks_count = 16
    overrides: dict[str, list[dict]] = {}
    if sessions:
        rows_by_id = {s.id: s for s in sessions}
        for occ in db.execute(
            select(SessionOccurrence).where(
                SessionOccurrence.session_id.in_(list(rows_by_id)),
                SessionOccurrence.week_start >= first_week,
                SessionOccurrence.week_start < first_week + timedelta(weeks=weeks_count),
            )
        ).scalars():
            row = rows_by_id[occ.session_id]
            slot = effective_slot(row, occ)
            overrides.setdefault(str(row.id), []).append({
                "week_start": occ.week_start,
                "not_held": live_status(occ).value == "not_held",
                "moved": is_moved(occ),
                "day_of_week": slot.day_of_week,
                "start_time": slot.start_time.isoformat(),
                "end_time": slot.end_time.isoformat(),
                "venue": slot.venue,
            })

    ics_content = generate_cohort_ics(
        cohort.code,
        items,
        version_label=version.label,
        weeks_count=weeks_count,
        start_monday=first_week,
        overrides=overrides,
    )

    filename = f"{cohort.code}_timetable.ics"
    return Response(
        content=ics_content,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "public, max-age=3600",
        },
    )

