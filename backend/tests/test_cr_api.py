"""Class-representative API: scoping, live status, reschedule, institute views."""
from __future__ import annotations

from datetime import time

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from app.api import cr as cr_api
from app.core.db import SessionLocal, atomic
from app.main import app
from app.models import (
    AcademicPeriod,
    AdminRole,
    AuditEvent,
    Cohort,
    Course,
    Institution,
    LiveStatus,
    Programme,
    ProgrammeLevel,
    Semester,
    SessionCohort,
    SourceDocument,
    TimetableSession,
    TimetableVersion,
    Venue,
    VersionStatus,
)
from app.services import create_admin, create_cr

PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def _clear_throttle():
    cr_api._ATTEMPTS.clear()
    yield
    cr_api._ATTEMPTS.clear()


def _seed() -> dict:
    """A published version with one cohort/session, plus a second unrelated cohort."""
    db = SessionLocal()
    try:
        inst = Institution(name="DIT", code="DIT")
        db.add(inst)
        db.flush()
        prog = Programme(institution_id=inst.id, name="Computer Engineering", code="COE",
                         level=ProgrammeLevel.diploma)
        db.add(prog)
        db.flush()
        cohort = Cohort(programme_id=prog.id, code="OD24COE-1", intake_year=24, section="1")
        other = Cohort(programme_id=prog.id, code="OD24COE-2", intake_year=24, section="2")
        db.add_all([cohort, other])
        period = AcademicPeriod(institution_id=inst.id, year_label="2025/2026", semester=Semester.s1)
        db.add(period)
        db.flush()
        src = SourceDocument(period_id=period.id, original_filename="t.pdf", sha256="c" * 64,
                             page_count=1, storage_key="sources/c.pdf")
        db.add(src)
        db.flush()
        version = TimetableVersion(period_id=period.id, source_document_id=src.id, label="v1",
                                   status=VersionStatus.published, is_active=True)
        db.add(version)
        db.flush()
        course = Course(name="Web Application Development", code="TEST 1001", department="ICT")
        venue_a = Venue(code="Room A")
        venue_b = Venue(code="Room B")
        db.add_all([course, venue_a, venue_b])
        db.flush()
        s1 = TimetableSession(version_id=version.id, day_of_week=1, start_time=time(8, 0),
                              end_time=time(10, 0), course_id=course.id,
                              course_name_raw=course.name, course_code_raw=course.code,
                              venue_id=venue_a.id, venue_raw="Room A", source_page=10,
                              source_text_raw="raw", confidence="high")
        s2 = TimetableSession(version_id=version.id, day_of_week=1, start_time=time(10, 0),
                              end_time=time(12, 0), course_id=course.id,
                              course_name_raw="Other", course_code_raw="TEST 2002",
                              venue_id=venue_b.id, venue_raw="Room B", source_page=11,
                              source_text_raw="raw", confidence="high")
        db.add_all([s1, s2])
        db.flush()
        db.add(SessionCohort(session_id=s1.id, cohort_id=cohort.id))
        db.add(SessionCohort(session_id=s2.id, cohort_id=other.id))
        with atomic(db):
            create_cr(db, email="cr@dit.ac.tz", password=PASSWORD, cohort_codes=["OD24COE-1"],
                      display_name="Class Rep")
        db.commit()
        return {"cohort": cohort.code, "other": other.code, "s1": str(s1.id), "s2": str(s2.id),
                "version": str(version.id)}
    finally:
        db.close()


def _login(client: TestClient) -> str:
    resp = client.post("/api/v1/cr/auth/login",
                       json={"email": "cr@dit.ac.tz", "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    return client.cookies.get("tt_csrf")


def _csrf(csrf: str) -> dict:
    return {"X-CSRF-Token": csrf}


def _add_session(cohort_code, *, day, start, end, venue_code, course_code="TEST 3003",
                 name="Extra class") -> str:
    """Add one more session to an existing cohort (for swap tests)."""
    db = SessionLocal()
    try:
        cohort = db.execute(select(Cohort).where(Cohort.code == cohort_code)).scalar_one()
        version = db.execute(select(TimetableVersion)).scalars().first()
        venue = db.execute(select(Venue).where(Venue.code == venue_code)).scalar_one()
        row = TimetableSession(version_id=version.id, day_of_week=day, start_time=start,
                               end_time=end, course_name_raw=name, course_code_raw=course_code,
                               venue_id=venue.id, venue_raw=venue_code, source_page=12,
                               source_text_raw="raw", confidence="high")
        db.add(row)
        db.flush()
        db.add(SessionCohort(session_id=row.id, cohort_id=cohort.id))
        db.commit()
        return str(row.id)
    finally:
        db.close()


def test_cr_login_and_me():
    ids = _seed()
    client = TestClient(app)
    me = _login(client)
    info = client.get("/api/v1/cr/auth/me").json()
    assert info["role"] == "cr"
    assert info["display_name"] == "Class Rep"
    assert [c["code"] for c in info["cohorts"]] == [ids["cohort"]]


def test_admin_cannot_use_cr_and_cr_cannot_use_admin():
    _seed()
    # A plain admin is rejected by the CR surface.
    db = SessionLocal()
    try:
        with atomic(db):
            create_admin(db, "owner@dit.ac.tz", PASSWORD, AdminRole.owner)
    finally:
        db.close()
    admin = TestClient(app)
    admin.post("/api/v1/admin/auth/login", json={"email": "owner@dit.ac.tz", "password": PASSWORD})
    assert admin.post("/api/v1/cr/auth/login",
                      json={"email": "owner@dit.ac.tz", "password": PASSWORD}).status_code == 403

    # A CR gets 403 on the staff admin API.
    cr = TestClient(app)
    _login(cr)
    assert cr.get("/api/v1/admin/versions").status_code == 403


def test_live_status_visible_to_public():
    ids = _seed()
    client = TestClient(app)
    csrf = _login(client)

    tt = client.get("/api/v1/cr/timetable", params={"cohort_code": ids["cohort"]}).json()
    assert len(tt["sessions"]) == 1

    resp = client.post(f"/api/v1/cr/sessions/{ids['s1']}/live",
                       json={"status": "live"}, headers=_csrf(csrf))
    assert resp.status_code == 200, resp.text
    assert resp.json()["live_status"] == "live"

    public = client.get("/api/v1/timetable", params={"cohort_code": ids["cohort"]}).json()
    assert public["sessions"][0]["live_status"] == "live"
    assert public["sessions"][0]["live_started_at"]

    # not_held later
    resp = client.post(f"/api/v1/cr/sessions/{ids['s1']}/live",
                       json={"status": "not_held"}, headers=_csrf(csrf))
    assert resp.json()["live_status"] == "not_held"


def test_reschedule_visible_to_public_and_audited():
    ids = _seed()
    client = TestClient(app)
    csrf = _login(client)
    resp = client.post(f"/api/v1/cr/sessions/{ids['s1']}/reschedule",
                       json={"start_time": "11:00", "end_time": "13:00", "venue": "Room Z",
                             "reason": "lecturer unavailable"}, headers=_csrf(csrf))
    assert resp.status_code == 200, resp.text
    assert resp.json()["start_time"] == "11:00:00"
    assert resp.json()["original_start_time"] == "08:00:00"

    public = client.get("/api/v1/timetable", params={"cohort_code": ids["cohort"]}).json()
    s = public["sessions"][0]
    assert s["start_time"] == "11:00:00"
    assert s["rescheduled"] is True
    assert s["original_start_time"] == "08:00:00"
    assert s["venue"] == "Room Z"

    db = SessionLocal()
    try:
        actions = {a.action for a in db.execute(select(AuditEvent)).scalars()}
    finally:
        db.close()
    assert "cr.reschedule" in actions


def test_cr_cannot_touch_other_cohort():
    ids = _seed()
    client = TestClient(app)
    csrf = _login(client)
    resp = client.post(f"/api/v1/cr/sessions/{ids['s2']}/live",
                       json={"status": "live"}, headers=_csrf(csrf))
    assert resp.status_code == 403


def test_institute_and_availability():
    _seed()
    client = TestClient(app)
    _login(client)
    inst = client.get("/api/v1/cr/institute", params={"day": 1}).json()
    assert len(inst["sessions"]) == 2

    avail = client.get("/api/v1/cr/availability",
                       params={"day": 1, "start": "08:00", "end": "10:00"}).json()
    by_code = {v["venue"]: v["free"] for v in avail["venues"]}
    assert by_code["Room A"] is False  # occupied 08:00-10:00
    assert by_code["Room B"] is True


def test_venue_notice_flow_and_availability():
    _seed()
    client = TestClient(app)
    csrf = _login(client)

    # Create a heads-up for Room B at 12:00 (free at that time).
    resp = client.post("/api/v1/cr/venue-notices",
                       json={"venue": "Room B", "day_of_week": 1, "start_time": "12:00",
                             "end_time": "13:00", "note": "moving our class here"},
                       headers=_csrf(csrf))
    assert resp.status_code == 200, resp.text
    notice_id = resp.json()["id"]

    # Visible to the public (students) too.
    public = client.get("/api/v1/venue-notices", params={"day": 1}).json()
    assert any(n["venue"] == "Room B" for n in public["notices"])

    # Availability now treats Room B as unavailable for that window.
    avail = client.get("/api/v1/cr/availability",
                       params={"day": 1, "start": "12:00", "end": "13:00"}).json()
    room_b = next(v for v in avail["venues"] if v["venue"] == "Room B")
    assert room_b["free"] is False
    assert room_b["notice"]["note"] == "moving our class here"

    # Clearing it makes the venue free again.
    assert client.delete(f"/api/v1/cr/venue-notices/{notice_id}",
                         headers=_csrf(csrf)).status_code == 200
    avail2 = client.get("/api/v1/cr/availability",
                        params={"day": 1, "start": "12:00", "end": "13:00"}).json()
    room_b2 = next(v for v in avail2["venues"] if v["venue"] == "Room B")
    assert room_b2["free"] is True
    assert room_b2["notice"] is None


def test_move_to_another_day_visible_to_public():
    ids = _seed()
    client = TestClient(app)
    csrf = _login(client)
    resp = client.post(f"/api/v1/cr/sessions/{ids['s1']}/reschedule",
                       json={"start_time": "09:00", "end_time": "11:00", "day_of_week": 3,
                             "reason": "agreed with lecturer"}, headers=_csrf(csrf))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["day_of_week"] == 3
    assert body["original_day_of_week"] == 1
    assert body["original_start_time"] == "08:00:00"

    public = client.get("/api/v1/timetable", params={"cohort_code": ids["cohort"]}).json()
    s = public["sessions"][0]
    assert s["day_of_week"] == 3
    assert s["original_day_of_week"] == 1
    assert s["rescheduled"] is True


def test_move_back_to_original_clears_reschedule():
    ids = _seed()
    client = TestClient(app)
    csrf = _login(client)
    first = client.post(f"/api/v1/cr/sessions/{ids['s1']}/reschedule",
                        json={"start_time": "09:00", "end_time": "11:00", "day_of_week": 3},
                        headers=_csrf(csrf))
    assert first.status_code == 200
    back = client.post(f"/api/v1/cr/sessions/{ids['s1']}/reschedule",
                       json={"start_time": "08:00", "end_time": "10:00", "day_of_week": 1},
                       headers=_csrf(csrf))
    assert back.status_code == 200, back.text
    assert back.json()["rescheduled"] is False
    assert back.json()["original_day_of_week"] is None


def test_swap_sessions_exchanges_slots_and_audits():
    ids = _seed()
    s3 = _add_session(ids["cohort"], day=3, start=time(10, 0), end=time(12, 0), venue_code="Room B")
    client = TestClient(app)
    csrf = _login(client)
    resp = client.post(f"/api/v1/cr/sessions/{ids['s1']}/swap",
                       json={"with_session_id": s3, "reason": "agreed swap"}, headers=_csrf(csrf))
    assert resp.status_code == 200, resp.text
    by_id = {s["id"]: s for s in resp.json()["sessions"]}
    a, b = by_id[ids["s1"]], by_id[s3]
    # s1 (Mon 08-10 Room A) takes s3's Wed 10-12 Room B slot, and vice versa.
    assert (a["day_of_week"], a["start_time"], a["end_time"], a["venue"]) == (3, "10:00:00", "12:00:00", "Room B")
    assert (b["day_of_week"], b["start_time"], b["end_time"], b["venue"]) == (1, "08:00:00", "10:00:00", "Room A")
    assert a["original_day_of_week"] == 1
    assert b["original_day_of_week"] == 3

    db = SessionLocal()
    try:
        actions = {x.action for x in db.execute(select(AuditEvent)).scalars()}
    finally:
        db.close()
    assert "cr.swap" in actions


def test_swap_rejects_session_outside_cohorts():
    ids = _seed()
    client = TestClient(app)
    csrf = _login(client)
    # s2 belongs to OD24COE-2, which this CR does not manage.
    resp = client.post(f"/api/v1/cr/sessions/{ids['s1']}/swap",
                       json={"with_session_id": ids["s2"]}, headers=_csrf(csrf))
    assert resp.status_code == 403


def test_swap_rejects_self():
    ids = _seed()
    client = TestClient(app)
    csrf = _login(client)
    resp = client.post(f"/api/v1/cr/sessions/{ids['s1']}/swap",
                       json={"with_session_id": ids["s1"]}, headers=_csrf(csrf))
    assert resp.status_code == 422

