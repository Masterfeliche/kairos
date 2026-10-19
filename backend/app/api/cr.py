"""Class-representative API (docs/07-api-specification.md).

CRs sign in with admin-issued accounts (role ``cr``) scoped to one or more cohorts.
They can view their class timetable, mark a session live at class start, reschedule a
session, and browse the whole-institute timetable / free rooms to find an open slot.
"""
from __future__ import annotations

import time as _time
from collections import defaultdict
from datetime import date, time
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    CSRF_COOKIE,
    CSRF_HEADER,
    SESSION_COOKIE,
    client_ip,
    get_current_cr,
    verify_csrf,
)
from app.core.campus import resolve_week
from app.core.config import settings
from app.core.db import atomic, get_session
from app.core.security import generate_token
from app.models import AdminRole, AdminUser, Cohort, LiveStatus, SessionCohort, TimetableSession
from app.services import audit_record
from app.services.auth_service import AuthError, authenticate, issue_session, revoke_session
from app.services.cr_service import (
    CrError,
    clear_venue_notice,
    create_venue_notice,
    cr_cohorts,
    institute_sessions,
    list_venue_notices,
    reschedule_session,
    room_availability,
    set_live_status,
    swap_sessions,
)
from app.services.session_view import serialize_for_week, session_to_dict
from app.services.version_service import require_live_version

router = APIRouter(prefix="/api/v1/cr", tags=["cr"])

_ATTEMPTS: dict[str, list[float]] = defaultdict(list)
_WINDOW = 300
_MAX = 5


def _throttle(ip: str) -> None:
    now = _time.time()
    attempts = [t for t in _ATTEMPTS[ip] if now - t < _WINDOW]
    _ATTEMPTS[ip] = attempts
    if len(attempts) >= _MAX:
        raise HTTPException(status_code=429, detail="Too many login attempts; try later.")
    attempts.append(now)


def _live_version(db: Session):
    # In production this is the active published version; in dev draft-preview mode it
    # is the latest review version.
    return require_live_version(db, preview=settings.allow_draft_preview)


def _cohort_out(c: Cohort) -> dict:
    return {"id": str(c.id), "code": c.code, "intake_year": c.intake_year, "section": c.section}


# --- auth -----------------------------------------------------------------

class LoginIn(BaseModel):
    email: EmailStr
    password: str


class MeOut(BaseModel):
    id: str
    email: str
    role: str
    display_name: str | None = None
    cohorts: list[dict]


def _set_cookies(response: Response, token: str, csrf: str) -> None:
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax",
                        secure=settings.secure_cookies, path="/", max_age=8 * 3600)
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, samesite="lax",
                        secure=settings.secure_cookies, path="/", max_age=8 * 3600)


@router.post("/auth/login", response_model=MeOut)
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_session)):
    ip = client_ip(request)
    _throttle(ip)
    try:
        user = authenticate(db, body.email, body.password)
    except AuthError:
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    if user.role != AdminRole.cr:
        raise HTTPException(status_code=403, detail="Not a class-representative account.")
    with atomic(db):
        token, _ = issue_session(db, user, user_agent=request.headers.get("user-agent"), ip=ip)
        audit_record(db, actor=user, action="cr.login", entity_type="admin_user",
                     entity_id=str(user.id), ip=ip)
    _set_cookies(response, token, generate_token(24))
    return _me(db, user)


@router.post("/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_session),
           _: None = Depends(verify_csrf)):
    with atomic(db):
        revoke_session(db, request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"ok": True}


def _me(db: Session, user: AdminUser) -> MeOut:
    return MeOut(id=str(user.id), email=user.email, role=user.role.value,
                 display_name=user.display_name,
                 cohorts=[_cohort_out(c) for c in cr_cohorts(db, user)])


@router.get("/auth/me", response_model=MeOut)
def me(user: AdminUser = Depends(get_current_cr), db: Session = Depends(get_session)):
    return _me(db, user)


# --- timetable ------------------------------------------------------------

@router.get("/timetable")
def my_timetable(
    cohort_code: str | None = Query(None),
    week: date | None = Query(None, description="Any date in the teaching week (default: this week)"),
    user: AdminUser = Depends(get_current_cr),
    db: Session = Depends(get_session),
):
    cohorts = cr_cohorts(db, user)
    if not cohorts:
        raise HTTPException(status_code=403, detail="No cohort assigned to this account.")
    if cohort_code:
        cohort = next((c for c in cohorts if c.code == cohort_code.upper()), None)
        if cohort is None:
            raise HTTPException(status_code=403, detail="Cohort not assigned to you.")
    else:
        cohort = cohorts[0]

    version, is_preview = _live_version(db)
    sessions = db.execute(
        select(TimetableSession)
        .join(SessionCohort, SessionCohort.session_id == TimetableSession.id)
        .where(SessionCohort.cohort_id == cohort.id, TimetableSession.version_id == version.id)
    ).scalars().all()
    wk = resolve_week(week)
    items = serialize_for_week(db, sessions, wk, base_cohort_code=cohort.code)
    return {
        "cohort": _cohort_out(cohort),
        "my_cohorts": [_cohort_out(c) for c in cohorts],
        "version": {"id": str(version.id), "label": version.label,
                    "status": version.status.value, "is_preview": is_preview},
        "week_start": wk.isoformat(),
        "sessions": items,
    }


@router.get("/institute")
def institute(
    day: int | None = Query(None, ge=1, le=7),
    week: date | None = Query(None, description="Any date in the teaching week (default: this week)"),
    user: AdminUser = Depends(get_current_cr),
    db: Session = Depends(get_session),
):
    version, is_preview = _live_version(db)
    wk = resolve_week(week)
    sessions, occurrences = institute_sessions(db, user, version=version, week=wk, day=day)
    items = serialize_for_week(db, sessions, wk, occurrences=occurrences)
    return {
        "version": {"id": str(version.id), "label": version.label,
                    "status": version.status.value, "is_preview": is_preview},
        "week_start": wk.isoformat(),
        "sessions": items,
    }


@router.get("/availability")
def availability(
    day: int = Query(..., ge=1, le=7),
    start: str = Query(..., description="HH:MM"),
    end: str = Query(..., description="HH:MM"),
    week: date | None = Query(None, description="Any date in the teaching week (default: this week)"),
    user: AdminUser = Depends(get_current_cr),
    db: Session = Depends(get_session),
):
    try:
        start_t = time.fromisoformat(start)
        end_t = time.fromisoformat(end)
    except ValueError:
        raise HTTPException(status_code=422, detail="Times must be HH:MM.")
    if end_t <= start_t:
        raise HTTPException(status_code=422, detail="End must be after start.")
    version, _ = _live_version(db)
    wk = resolve_week(week)
    return {"day": day, "start": start_t.isoformat(), "end": end_t.isoformat(),
            "week_start": wk.isoformat(),
            "venues": room_availability(db, user, version=version, day=day,
                                        start_time=start_t, end_time=end_t, week=wk)}


# --- venue notices --------------------------------------------------------

class VenueNoticeIn(BaseModel):
    venue: str
    week: date | None = None
    day_of_week: int
    start_time: str
    end_time: str | None = None
    note: str | None = None


@router.get("/venue-notices")
def get_venue_notices(
    day: int | None = Query(None, ge=1, le=7),
    week: date | None = Query(None, description="Any date in the teaching week (default: this week)"),
    user: AdminUser = Depends(get_current_cr),
    db: Session = Depends(get_session),
):
    return {"notices": list_venue_notices(db, day=day, week=week)}


@router.post("/venue-notices")
def post_venue_notice(
    body: VenueNoticeIn,
    request: Request,
    user: AdminUser = Depends(get_current_cr),
    db: Session = Depends(get_session),
    _: None = Depends(verify_csrf),
):
    if not 1 <= body.day_of_week <= 7:
        raise HTTPException(status_code=422, detail="day_of_week must be 1-7.")
    try:
        start_t = time.fromisoformat(body.start_time)
        end_t = time.fromisoformat(body.end_time) if body.end_time else None
    except ValueError:
        raise HTTPException(status_code=422, detail="Times must be HH:MM.")
    with atomic(db):
        try:
            notice = create_venue_notice(db, user=user, venue=body.venue, day_of_week=body.day_of_week,
                                         start_time=start_t, end_time=end_t, note=body.note, week=body.week,
                                         ip=client_ip(request))
        except CrError as exc:
            raise _cr_error(exc)
    return {"id": str(notice.id), "venue": notice.venue,
            "start_time": notice.start_time.isoformat(),
            "end_time": notice.end_time.isoformat() if notice.end_time else None}


@router.delete("/venue-notices/{notice_id}")
def delete_venue_notice(
    notice_id: UUID,
    request: Request,
    user: AdminUser = Depends(get_current_cr),
    db: Session = Depends(get_session),
    _: None = Depends(verify_csrf),
):
    with atomic(db):
        try:
            clear_venue_notice(db, user=user, notice_id=notice_id, ip=client_ip(request))
        except CrError as exc:
            raise _cr_error(exc)
    return {"ok": True}


# --- mutations ------------------------------------------------------------

class LiveIn(BaseModel):
    status: Literal["live", "ended", "not_held", "scheduled"]
    week: date | None = None  # any date in the teaching week; default this week


class RescheduleIn(BaseModel):
    start_time: str
    end_time: str
    day_of_week: int | None = None
    venue: str | None = None
    reason: str | None = None
    week: date | None = None


class SwapIn(BaseModel):
    with_session_id: UUID
    reason: str | None = None
    week: date | None = None


def _occurrence_out(row: TimetableSession, occ) -> dict:
    """The week's view of one session, in the same shape as the timetable endpoints."""
    d = session_to_dict(row, occurrence=occ)
    keys = ("id", "day_of_week", "start_time", "end_time", "venue", "live_status",
            "live_started_at", "live_ended_at", "rescheduled", "reschedule_reason",
            "original_day_of_week", "original_start_time", "original_end_time", "original_venue")
    return {k: d[k] for k in keys}


def _cr_error(exc: CrError) -> HTTPException:
    msg = str(exc)
    code = 404 if "not found" in msg.lower() else 403 if "not in one of your cohorts" in msg else 422
    return HTTPException(status_code=code, detail=msg)


@router.post("/sessions/{session_id}/live")
def set_live(
    session_id: UUID,
    body: LiveIn,
    request: Request,
    user: AdminUser = Depends(get_current_cr),
    db: Session = Depends(get_session),
    _: None = Depends(verify_csrf),
):
    with atomic(db):
        try:
            row, occ = set_live_status(db, user=user, session_id=session_id,
                                       status=LiveStatus(body.status), week=body.week,
                                       ip=client_ip(request))
        except CrError as exc:
            raise _cr_error(exc)
    return {**_occurrence_out(row, occ), "week_start": resolve_week(body.week).isoformat()}


@router.post("/sessions/{session_id}/reschedule")
def reschedule(
    session_id: UUID,
    body: RescheduleIn,
    request: Request,
    user: AdminUser = Depends(get_current_cr),
    db: Session = Depends(get_session),
    _: None = Depends(verify_csrf),
):
    try:
        start_t = time.fromisoformat(body.start_time)
        end_t = time.fromisoformat(body.end_time)
    except ValueError:
        raise HTTPException(status_code=422, detail="Times must be HH:MM.")
    if body.day_of_week is not None and not 1 <= body.day_of_week <= 7:
        raise HTTPException(status_code=422, detail="day_of_week must be 1-7.")
    with atomic(db):
        try:
            row, occ = reschedule_session(db, user=user, session_id=session_id,
                                          start_time=start_t, end_time=end_t,
                                          day_of_week=body.day_of_week, venue=body.venue,
                                          reason=body.reason, week=body.week,
                                          ip=client_ip(request))
        except CrError as exc:
            raise _cr_error(exc)
    return {**_occurrence_out(row, occ), "week_start": resolve_week(body.week).isoformat()}


@router.post("/sessions/{session_id}/swap")
def swap(
    session_id: UUID,
    body: SwapIn,
    request: Request,
    user: AdminUser = Depends(get_current_cr),
    db: Session = Depends(get_session),
    _: None = Depends(verify_csrf),
):
    with atomic(db):
        try:
            pairs = swap_sessions(db, user=user, session_id=session_id,
                                  with_session_id=body.with_session_id, reason=body.reason,
                                  week=body.week, ip=client_ip(request))
        except CrError as exc:
            raise _cr_error(exc)
    return {"week_start": resolve_week(body.week).isoformat(),
            "sessions": [_occurrence_out(row, occ) for row, occ in pairs]}
