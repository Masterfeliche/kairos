"""Import pipeline tests: complete draft + clean failure (Phase 2 DoD)."""
from __future__ import annotations

from sqlalchemy import func, select

from app.models import (
    Cohort,
    Course,
    SourceDocument,
    TimetableSession,
    TimetableVersion,
    ValidationIssue,
    VersionStatus,
)
from app.services import import_pdf


def test_import_creates_complete_draft(session, pdf_path):
    summary = import_pdf(session, pdf_path)

    version = session.get(TimetableVersion, summary.version_id)
    assert version is not None
    assert version.status == VersionStatus.review
    assert version.is_active is False

    n_sessions = session.execute(
        select(func.count()).select_from(TimetableSession).where(
            TimetableSession.version_id == version.id
        )
    ).scalar_one()
    assert n_sessions == summary.sessions
    assert n_sessions > 1900

    # Provenance recorded.
    assert session.execute(select(func.count()).select_from(SourceDocument)).scalar_one() == 1
    assert session.execute(select(func.count()).select_from(Course)).scalar_one() > 50
    assert session.execute(select(func.count()).select_from(Cohort)).scalar_one() > 50

    # Issues recorded and every missing-code session is low confidence.
    issues = session.execute(
        select(ValidationIssue).where(ValidationIssue.version_id == version.id)
    ).scalars().all()
    assert issues
    assert any(i.code == "MISSING_CODE" for i in issues)


def test_import_is_idempotent_on_source_hash(session, pdf_path):
    a = import_pdf(session, pdf_path)
    b = import_pdf(session, pdf_path)
    # Same source document is reused (hash-addressed), but two distinct versions exist.
    assert session.execute(select(func.count()).select_from(SourceDocument)).scalar_one() == 1
    assert a.version_id != b.version_id
    assert session.execute(select(func.count()).select_from(TimetableVersion)).scalar_one() == 2


def test_failed_import_leaves_db_clean(session, tmp_path):
    bad = tmp_path / "not_a.pdf"
    bad.write_text("this is not a pdf")

    import pytest

    with pytest.raises(ValueError):
        import_pdf(session, bad)

    # Nothing was persisted.
    session.rollback()
    assert session.execute(select(func.count()).select_from(TimetableVersion)).scalar_one() == 0
    assert session.execute(select(func.count()).select_from(TimetableSession)).scalar_one() == 0
    assert session.execute(select(func.count()).select_from(SourceDocument)).scalar_one() == 0
