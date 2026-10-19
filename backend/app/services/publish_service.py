"""Atomic publish / rollback (docs/05-system-architecture.md §6.4).

Publishing touches active data only, in one transaction, guarded by the partial unique
index ``uq_one_active_version_per_period``. Rollback re-publishes a previous version;
nothing is ever deleted.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import atomic
from app.models import (
    PublicationAction,
    PublicationRecord,
    TimetableVersion,
    ValidationIssue,
    VersionStatus,
)
from app.models import IssueSeverity
from app.services.occurrence_service import carry_forward


class PublishError(Exception):
    pass


def _as_uuid(value) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def publish(session: Session, version_id) -> PublicationRecord:
    version_id = _as_uuid(version_id)
    with atomic(session):
        version = session.get(TimetableVersion, version_id)
        if version is None:
            raise PublishError("Version not found.")
        if version.status not in (VersionStatus.review, VersionStatus.draft):
            raise PublishError(f"Cannot publish a version in status {version.status.value}.")

        blocking = session.execute(
            select(ValidationIssue).where(
                ValidationIssue.version_id == version.id,
                ValidationIssue.severity == IssueSeverity.error,
                ValidationIssue.resolved_at.is_(None),
            )
        ).scalars().first()
        if blocking is not None:
            raise PublishError("Version has unresolved error-level issues.")

        current = session.execute(
            select(TimetableVersion).where(
                TimetableVersion.period_id == version.period_id,
                TimetableVersion.is_active.is_(True),
            )
        ).scalar_one_or_none()

        previous_id = None
        if current is not None and current.id != version.id:
            current.is_active = False
            current.status = VersionStatus.superseded
            previous_id = current.id
            # Flush the deactivation first: the partial unique index on
            # (period_id) WHERE is_active must never see two active rows.
            session.flush()

        version.is_active = True
        version.status = VersionStatus.published
        version.published_at = datetime.now(timezone.utc)

        # Class-rep changes for this and future weeks follow the class to the new version.
        carry_forward(session, previous_id, version.id)

        record = PublicationRecord(
            version_id=version.id,
            action=PublicationAction.publish,
            previous_version_id=previous_id,
        )
        session.add(record)
        return record


def rollback(session: Session, period_id, to_version_id) -> PublicationRecord:
    period_id = _as_uuid(period_id)
    to_version_id = _as_uuid(to_version_id)
    with atomic(session):
        target = session.get(TimetableVersion, to_version_id)
        if target is None or target.period_id != period_id:
            raise PublishError("Target version not found for this period.")

        current = session.execute(
            select(TimetableVersion).where(
                TimetableVersion.period_id == period_id,
                TimetableVersion.is_active.is_(True),
            )
        ).scalar_one_or_none()

        previous_id = None
        if current is not None and current.id != target.id:
            current.is_active = False
            current.status = VersionStatus.superseded
            previous_id = current.id
            session.flush()

        target.is_active = True
        target.status = VersionStatus.published
        target.published_at = datetime.now(timezone.utc)

        carry_forward(session, previous_id, target.id)

        record = PublicationRecord(
            version_id=target.id,
            action=PublicationAction.rollback,
            previous_version_id=previous_id,
        )
        session.add(record)
        return record
