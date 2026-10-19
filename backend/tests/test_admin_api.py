"""Phase 3 admin console: auth, CSRF, review, corrections, audit, publish gating."""
from __future__ import annotations

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
import uuid

from app.api import admin_auth
from app.core.db import SessionLocal, atomic
from app.main import app
from app.models import (
    AcademicPeriod,
    AdminRole,
    AuditEvent,
    Institution,
    Semester,
    SourceDocument,
    TimetableVersion,
    VersionStatus,
)
from app.services import create_admin

PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def _clear_login_throttle():
    admin_auth._ATTEMPTS.clear()
    yield
    admin_auth._ATTEMPTS.clear()


def _make_admin(email: str, role: AdminRole) -> None:
    db = SessionLocal()
    try:
        with atomic(db):
            create_admin(db, email, PASSWORD, role)
    finally:
        db.close()


def _login(client: TestClient, email: str) -> str:
    resp = client.post("/api/v1/admin/auth/login",
                       json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    return client.cookies.get("tt_csrf")


def _csrf_headers(csrf: str) -> dict:
    return {"X-CSRF-Token": csrf}


def test_admin_endpoints_require_auth():
    client = TestClient(app)
    assert client.get("/api/v1/admin/versions").status_code == 401
    assert client.get("/api/v1/admin/auth/me").status_code == 401


def test_login_me_logout_roundtrip():
    _make_admin("owner@dit.ac.tz", AdminRole.owner)
    client = TestClient(app)

    assert client.post("/api/v1/admin/auth/login",
                       json={"email": "owner@dit.ac.tz", "password": "wrong"}).status_code == 401

    csrf = _login(client, "owner@dit.ac.tz")
    assert csrf
    me = client.get("/api/v1/admin/auth/me").json()
    assert me["role"] == "owner"

    assert client.post("/api/v1/admin/auth/logout", headers=_csrf_headers(csrf)).status_code == 200
    assert client.get("/api/v1/admin/auth/me").status_code == 401


def test_csrf_required_for_mutations():
    _make_admin("owner@dit.ac.tz", AdminRole.owner)
    client = TestClient(app)
    _login(client, "owner@dit.ac.tz")
    # No CSRF header -> 403.
    resp = client.post("/api/v1/admin/import",
                       files={"file": ("x.pdf", b"%PDF-1.7 test", "application/pdf")})
    assert resp.status_code == 403


def test_import_review_and_correction_audited(pdf_path):
    _make_admin("owner@dit.ac.tz", AdminRole.owner)
    client = TestClient(app)
    csrf = _login(client, "owner@dit.ac.tz")

    import io
    with pdf_path.open("rb") as fh:
        resp = client.post(
            "/api/v1/admin/import",
            files={"file": ("timetable.pdf", io.BytesIO(fh.read()), "application/pdf")},
            data={"year_label": "2025/2026", "semester": "1", "label": "Semester I"},
            headers=_csrf_headers(csrf),
        )
    assert resp.status_code == 200, resp.text
    version_id = resp.json()["version_id"]

    detail = client.get(f"/api/v1/admin/versions/{version_id}").json()
    assert detail["sessions"] > 1000
    assert detail["open_errors"] > 0

    only_issues = client.get(f"/api/v1/admin/versions/{version_id}/sessions",
                             params={"only_issues": True, "size": 1}).json()
    assert only_issues["total"] > 0
    session_id = only_issues["items"][0]["id"]

    # Correct the session: supply a code and give a reason.
    resp = client.post(f"/api/v1/admin/sessions/{session_id}/correct",
                       json={"changes": {"course_code_raw": "TEST 9999"},
                             "reason": "read from source PDF page"},
                       headers=_csrf_headers(csrf))
    assert resp.status_code == 200, resp.text

    audit = client.get("/api/v1/admin/audit").json()
    actions = {a["action"] for a in audit}
    assert "session.correct" in actions
    assert "import.create" in actions

    # Duplicate import without force is rejected by SHA-256 dedupe.
    with pdf_path.open("rb") as fh:
        dup = client.post(
            "/api/v1/admin/import",
            files={"file": ("timetable.pdf", io.BytesIO(fh.read()), "application/pdf")},
            headers=_csrf_headers(csrf),
        )
    assert dup.status_code == 409


def _seed_clean_version() -> tuple[str, str, str]:
    db = SessionLocal()
    try:
        inst = Institution(name="DIT", code="DIT")
        db.add(inst)
        db.flush()
        period = AcademicPeriod(institution_id=inst.id, year_label="2025/2026",
                                semester=Semester.s1)
        db.add(period)
        db.flush()
        src = SourceDocument(period_id=period.id, original_filename="t.pdf", sha256="b" * 64,
                             page_count=1, storage_key="sources/b.pdf")
        db.add(src)
        db.flush()
        v1 = TimetableVersion(period_id=period.id, source_document_id=src.id,
                              label="v1", status=VersionStatus.review)
        v2 = TimetableVersion(period_id=period.id, source_document_id=src.id,
                              label="v2", status=VersionStatus.review)
        db.add_all([v1, v2])
        db.commit()
        return str(period.id), str(v1.id), str(v2.id)
    finally:
        db.close()


def test_publish_is_owner_only_and_audited():
    _make_admin("owner@dit.ac.tz", AdminRole.owner)
    _make_admin("reviewer@dit.ac.tz", AdminRole.reviewer)
    period_id, v1, v2 = _seed_clean_version()

    reviewer = TestClient(app)
    csrf = _login(reviewer, "reviewer@dit.ac.tz")
    denied = reviewer.post(f"/api/v1/admin/versions/{v1}/publish",
                           headers=_csrf_headers(csrf))
    assert denied.status_code == 403

    owner = TestClient(app)
    csrf = _login(owner, "owner@dit.ac.tz")
    assert owner.post(f"/api/v1/admin/versions/{v1}/publish",
                      headers=_csrf_headers(csrf)).status_code == 200
    resp = owner.post(f"/api/v1/admin/versions/{v2}/publish", headers=_csrf_headers(csrf))
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_active"] is True

    history = owner.get("/api/v1/admin/history").json()
    assert any(h["action"] == "publish" for h in history)

    # Rollback re-activates v1 and supersedes v2.
    resp = owner.post(f"/api/v1/admin/periods/{period_id}/rollback/{v1}",
                      headers=_csrf_headers(csrf))
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_active"] is True

    db = SessionLocal()
    try:
        actions = {a.action for a in db.execute(select(AuditEvent)).scalars()}
        v2_row = db.get(TimetableVersion, uuid.UUID(v2))
    finally:
        db.close()
    assert "version.publish" in actions
    assert "version.rollback" in actions
    assert v2_row.status == VersionStatus.superseded


def test_diff_endpoint(pdf_path):
    _make_admin("owner@dit.ac.tz", AdminRole.owner)
    client = TestClient(app)
    csrf = _login(client, "owner@dit.ac.tz")

    import io
    with pdf_path.open("rb") as fh:
        resp = client.post(
            "/api/v1/admin/import",
            files={"file": ("timetable.pdf", io.BytesIO(fh.read()), "application/pdf")},
            headers=_csrf_headers(csrf),
        )
    version_id = resp.json()["version_id"]

    diff = client.get(f"/api/v1/admin/versions/{version_id}/diff").json()
    assert diff["base_version_id"] is None
    assert diff["summary"]["added"] > 1000
