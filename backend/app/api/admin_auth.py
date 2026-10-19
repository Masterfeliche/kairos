"""Admin authentication endpoints (docs/07-api-specification.md §8.2)."""
from __future__ import annotations

import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api.deps import (
    CSRF_COOKIE,
    CSRF_HEADER,
    SESSION_COOKIE,
    client_ip,
    get_current_admin,
    verify_csrf,
)
from app.core.config import settings
from app.core.db import atomic, get_session
from app.core.security import generate_token
from app.models import AdminUser
from app.services import audit_record
from app.services.auth_service import AuthError, authenticate, issue_session, revoke_session

router = APIRouter(prefix="/api/v1/admin/auth", tags=["admin-auth"])

# Naive in-process login throttle: 5 attempts / 5 minutes / IP (docs/07 §8.3).
_ATTEMPTS: dict[str, list[float]] = defaultdict(list)
_WINDOW = 300
_MAX = 5


def _throttle(ip: str) -> None:
    now = time.time()
    attempts = [t for t in _ATTEMPTS[ip] if now - t < _WINDOW]
    _ATTEMPTS[ip] = attempts
    if len(attempts) >= _MAX:
        raise HTTPException(status_code=429, detail="Too many login attempts; try later.")
    attempts.append(now)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class MeOut(BaseModel):
    id: str
    email: str
    role: str


def _set_cookies(response: Response, token: str, csrf: str) -> None:
    response.set_cookie(
        SESSION_COOKIE, token, httponly=True, samesite="lax",
        secure=settings.secure_cookies, path="/", max_age=8 * 3600,
    )
    # CSRF cookie is intentionally readable by the SPA (double-submit pattern).
    response.set_cookie(
        CSRF_COOKIE, csrf, httponly=False, samesite="lax",
        secure=settings.secure_cookies, path="/", max_age=8 * 3600,
    )


@router.post("/login", response_model=MeOut)
def login(body: LoginIn, request: Request, response: Response,
          db: Session = Depends(get_session)):
    ip = client_ip(request)
    _throttle(ip)
    try:
        user = authenticate(db, body.email, body.password)
    except AuthError:
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    with atomic(db):
        token, _ = issue_session(db, user, user_agent=request.headers.get("user-agent"), ip=ip)
        audit_record(db, actor=user, action="auth.login", entity_type="admin_user",
                     entity_id=str(user.id), ip=ip)
    _set_cookies(response, token, generate_token(24))
    return MeOut(id=str(user.id), email=user.email, role=user.role.value)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_session),
           _: None = Depends(verify_csrf)):
    token = request.cookies.get(SESSION_COOKIE)
    with atomic(db):
        revoke_session(db, token)
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"ok": True}


@router.get("/me", response_model=MeOut)
def me(admin: AdminUser = Depends(get_current_admin)):
    return MeOut(id=str(admin.id), email=admin.email, role=admin.role.value)
