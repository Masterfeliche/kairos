"""Atomic publish / rollback tests (Phase 2 DoD)."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models import (
    AcademicPeriod,
    Institution,
    IssueSeverity,
    PublicationRecord,
    Semester,
    SourceDocument,
    TimetableVersion,
    ValidationIssue,
    VersionStatus,
)
from app.services import publish, rollback
from app.services.publish_service import PublishError


def _seed(session):
    inst = Institution(name="DIT", code="DIT")
    session.add(inst)
    session.flush()
    period = AcademicPeriod(institution_id=inst.id, year_label="2025/2026", semester=Semester.s1)
    session.add(period)
    session.flush()
    src = SourceDocument(period_id=period.id, original_filename="t.pdf", sha256="a" * 64,
                         page_count=160, storage_key="sources/a.pdf")
    session.add(src)
    session.flush()
    v1 = TimetableVersion(period_id=period.id, source_document_id=src.id, label="v1",
                          status=VersionStatus.review)
    v2 = TimetableVersion(period_id=period.id, source_document_id=src.id, label="v2",
                          status=VersionStatus.review)
    session.add_all([v1, v2])
    session.commit()
    return period, v1, v2


def test_publish_activates_and_supersedes(session):
    period, v1, v2 = _seed(session)

    publish(session, v1.id)
    session.expire_all()
    assert session.get(TimetableVersion, v1.id).is_active is True
    assert session.get(TimetableVersion, v1.id).status == VersionStatus.published

    # Publishing v2 supersedes v1 atomically.
    publish(session, v2.id)
    session.expire_all()
    assert session.get(TimetableVersion, v2.id).is_active is True
    assert session.get(TimetableVersion, v1.id).is_active is False
    assert session.get(TimetableVersion, v1.id).status == VersionStatus.superseded

    assert session.execute(select(PublicationRecord)).scalars().all()


def test_rollback_republishes_previous(session):
    period, v1, v2 = _seed(session)
    publish(session, v1.id)
    publish(session, v2.id)

    rollback(session, period.id, v1.id)
    session.expire_all()
    assert session.get(TimetableVersion, v1.id).is_active is True
    assert session.get(TimetableVersion, v2.id).status == VersionStatus.superseded


def test_publish_refused_when_errors_exist(session):
    period, v1, v2 = _seed(session)
    session.add(ValidationIssue(version_id=v1.id, code="MISSING_CODE",
                                severity=IssueSeverity.error, message="x", page=1))
    session.commit()

    with pytest.raises(PublishError):
        publish(session, v1.id)
    session.expire_all()
    assert session.get(TimetableVersion, v1.id).is_active is False
