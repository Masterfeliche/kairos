"""Auth / CSRF dependencies for the admin and CR APIs."""
from __future__ import annotations

from fastapi import Cookie, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.core.security import safe_equal
from app.models import AdminRole, AdminUser
from app.services.auth_service import resolve_session

SESSION_COOKIE = "tt_session"
CSRF_COOKIE = "tt_csrf"
CSRF_HEADER = "X-CSRF-Token"

_STAFF_ROLES = (AdminRole.admin, AdminRole.reviewer, AdminRole.owner)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def get_current_admin(
    tt_session: str | None = Cookie(default=None),
    db: Session = Depends(get_session),
) -> AdminUser:
    user = resolve_session(db, tt_session)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return user


def get_current_staff(admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
    """Back-office user (admin/reviewer/owner). Excludes class representatives."""
    if admin.role not in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff access required.")
    return admin


def require_owner(admin: AdminUser = Depends(get_current_staff)) -> AdminUser:
    if admin.role != AdminRole.owner:
        raise HTTPException(status_code=403, detail="Owner role required.")
    return admin


def get_current_cr(admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
    if admin.role != AdminRole.cr:
        raise HTTPException(status_code=403, detail="Class representative access required.")
    return admin


def verify_csrf(
    x_csrf_token: str | None = Header(default=None),
    tt_csrf: str | None = Cookie(default=None),
) -> None:
    """Double-submit CSRF check for state-changing requests."""
    if not safe_equal(x_csrf_token, tt_csrf):
        raise HTTPException(status_code=403, detail="Invalid or missing CSRF token.")
