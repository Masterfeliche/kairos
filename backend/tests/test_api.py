"""API smoke tests (TestClient, no server)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health():
    client = TestClient(app)
    assert client.get("/healthz").json() == {"status": "ok"}


def test_public_endpoints_empty():
    client = TestClient(app)
    assert client.get("/api/v1/cohorts").json() == []
    assert client.get("/api/v1/versions/active").status_code == 404
