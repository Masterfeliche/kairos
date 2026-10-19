"""Resolve which timetable version the public/CR surfaces should operate on.

Normal operation: the single active *published* version.
Dev/staging aid: when ``allow_draft_preview`` is on, fall back to the latest
`review` version so the site can be exercised before the publish gate is cleared.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import TimetableVersion, VersionStatus

_PREVIEW_STATUSES = (VersionStatus.review, VersionStatus.published)


def resolve_live_version(
    db: Session, period_id: uuid.UUID | None = None, *, preview: bool = False
) -> tuple[TimetableVersion, bool] | None:
    """Return ``(version, is_preview)`` or ``None`` when nothing is available."""
    active = db.execute(
        select(TimetableVersion).where(
            TimetableVersion.is_active.is_(True),
            TimetableVersion.status == VersionStatus.published,
        )
    ).scalars().first()
    if active is not None:
        return active, False
    if preview:
        stmt = select(TimetableVersion).where(TimetableVersion.status.in_(_PREVIEW_STATUSES))
        if period_id is not None:
            stmt = stmt.where(TimetableVersion.period_id == period_id)
        latest = db.execute(stmt.order_by(TimetableVersion.created_at.desc())).scalars().first()
        if latest is not None:
            return latest, True
    return None


def require_live_version(
    db: Session, period_id: uuid.UUID | None = None, *, preview: bool = False
) -> tuple[TimetableVersion, bool]:
    resolved = resolve_live_version(db, period_id, preview=preview)
    if resolved is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="No published version.")
    return resolved


def preview_allowed(requested: bool) -> bool:
    if requested and not settings.allow_draft_preview:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Draft preview is disabled.")
    return requested
