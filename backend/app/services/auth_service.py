"""Admin authentication & session lifecycle."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import generate_token, hash_password, hash_token, verify_password
from app.models import AdminRole, AdminSession, AdminUser

SESSION_TTL = timedelta(hours=8)


class AuthError(Exception):
    pass


def create_admin(session: Session, email: str, password: str,
                 role: AdminRole = AdminRole.owner,
                 display_name: str | None = None) -> AdminUser:
    email = email.strip().lower()
    existing = session.execute(select(AdminUser).where(AdminUser.email == email)).scalar_one_or_none()
    if existing is not None:
        raise AuthError(f"Admin '{email}' already exists.")
    if len(password) < 8:
        raise AuthError("Password must be at least 8 characters.")
    user = AdminUser(email=email, password_hash=hash_password(password), role=role,
                     display_name=display_name)
    session.add(user)
    session.flush()
    return user


def authenticate(session: Session, email: str, password: str) -> AdminUser:
    email = email.strip().lower()
    user = session.execute(select(AdminUser).where(AdminUser.email == email)).scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(user.password_hash, password):
        raise AuthError("Invalid credentials.")
    return user


def issue_session(session: Session, user: AdminUser, *, user_agent: str | None = None,
                  ip: str | None = None) -> tuple[str, AdminSession]:
    token = generate_token()
    s = AdminSession(
        token_hash=hash_token(token),
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + SESSION_TTL,
        user_agent=user_agent,
        ip=ip,
    )
    session.add(s)
    user.last_login_at = datetime.now(timezone.utc)
    session.flush()
    return token, s


def _aware(dt: datetime) -> datetime:
    """SQLite returns naive datetimes; treat them as UTC for comparisons."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def resolve_session(session: Session, token: str | None) -> AdminUser | None:
    if not token:
        return None
    s = session.execute(
        select(AdminSession).where(AdminSession.token_hash == hash_token(token))
    ).scalar_one_or_none()
    if s is None or s.revoked_at is not None:
        return None
    if _aware(s.expires_at) <= datetime.now(timezone.utc):
        return None
    user = session.get(AdminUser, s.user_id)
    if user is None or not user.is_active:
        return None
    return user


def revoke_session(session: Session, token: str | None) -> None:
    if not token:
        return
    s = session.execute(
        select(AdminSession).where(AdminSession.token_hash == hash_token(token))
    ).scalar_one_or_none()
    if s is not None and s.revoked_at is None:
        s.revoked_at = datetime.now(timezone.utc)
        session.flush()


def revoke_all_sessions(session: Session, user_id: uuid.UUID) -> int:
    rows = session.execute(
        select(AdminSession).where(AdminSession.user_id == user_id,
                                   AdminSession.revoked_at.is_(None))
    ).scalars().all()
    now = datetime.now(timezone.utc)
    for s in rows:
        s.revoked_at = now
    session.flush()
    return len(rows)
