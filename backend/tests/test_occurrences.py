"""Class-rep changes are date-scoped: they apply to one teaching week only."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api import cr as cr_api
from app.core.campus import current_week_start, resolve_week
from app.core.db import SessionLocal
from app.main import app
from app.models import (
    SessionCohort,
    SessionOccurrence,
    SourceDocument,
    TimetableSession,
    TimetableVersion,
    VersionStatus,
)
from app.services.publish_service import publish
from tests.test_cr_api import _add_session, _csrf, _login, _seed

THIS_WEEK = current_week_start()
NEXT_WEEK = THIS_WEEK + timedelta(days=7)


@pytest.fixture(autouse=True)
def _clear_throttle():
    cr_api._ATTEMPTS.clear()
    yield
    cr_api._ATTEMPTS.clear()


def _public(client: TestClient, cohort: str, week: date) -> list[dict]:
    resp = client.get("/api/v1/timetable", params={"cohort_code": cohort, "week": week.isoformat()})
    assert resp.status_code == 200, resp.text
    assert resp.json()["week_start"] == resolve_week(week).isoformat()
    return resp.json()["sessions"]


def _occurrences() -> list[SessionOccurrence]:
    db = SessionLocal()
    try:
        return list(db.execute(select(SessionOccurrence)).scalars())
    finally:
        db.close()


def test_week_helpers():
    assert resolve_week(date(2026, 10, 22)) == date(2026, 10, 19)  # Thu -> Mon
    # Saturday 17 Oct 2026, 10:00 EAT: "this week" is the coming one.
    sat = datetime(2026, 10, 17, 7, 0, tzinfo=timezone.utc)
    assert current_week_start(sat) == date(2026, 10, 19)
    # Sunday 23:30 UTC is already Monday 02:30 in EAT.
    late_sun = datetime(2026, 10, 18, 23, 30, tzinfo=timezone.utc)
    assert current_week_start(late_sun) == date(2026, 10, 19)


def test_status_does_not_leak_into_next_week():
    ids = _seed()
    client = TestClient(app)
    csrf = _login(client)
    resp = client.post(f"/api/v1/cr/sessions/{ids['s1']}/live",
                       json={"status": "not_held", "week": THIS_WEEK.isoformat()},
                       headers=_csrf(csrf))
    assert resp.status_code == 200, resp.text
    assert resp.json()["live_status"] == "not_held"

    assert _public(client, ids["cohort"], THIS_WEEK)[0]["live_status"] == "not_held"
    assert _public(client, ids["cohort"], NEXT_WEEK)[0]["live_status"] == "scheduled"
    # Any date inside the week resolves to the same week.
    assert _public(client, ids["cohort"], THIS_WEEK + timedelta(days=3))[0]["live_status"] == "not_held"


def test_status_defaults_to_this_week():
    ids = _seed()
    client = TestClient(app)
    csrf = _login(client)
    client.post(f"/api/v1/cr/sessions/{ids['s1']}/live", json={"status": "live"}, headers=_csrf(csrf))
    [occ] = _occurrences()
    assert occ.week_start == THIS_WEEK


def test_reset_to_scheduled_removes_the_override():
    ids = _seed()
    client = TestClient(app)
    csrf = _login(client)
    client.post(f"/api/v1/cr/sessions/{ids['s1']}/live", json={"status": "live"}, headers=_csrf(csrf))
    assert len(_occurrences()) == 1
    resp = client.post(f"/api/v1/cr/sessions/{ids['s1']}/live", json={"status": "scheduled"},
                       headers=_csrf(csrf))
    assert resp.json()["live_status"] == "scheduled"
    assert _occurrences() == []


def test_undo_end_class_keeps_original_start_time():
    ids = _seed()
    client = TestClient(app)
    csrf = _login(client)
    started = client.post(f"/api/v1/cr/sessions/{ids['s1']}/live", json={"status": "live"},
                          headers=_csrf(csrf)).json()["live_started_at"]
    client.post(f"/api/v1/cr/sessions/{ids['s1']}/live", json={"status": "ended"}, headers=_csrf(csrf))
    resumed = client.post(f"/api/v1/cr/sessions/{ids['s1']}/live", json={"status": "live"},
                          headers=_csrf(csrf)).json()
    assert resumed["live_status"] == "live"
    assert resumed["live_started_at"] == started
    assert resumed["live_ended_at"] is None


def test_move_applies_only_to_that_week_and_template_is_untouched():
    ids = _seed()
    client = TestClient(app)
    csrf = _login(client)
    resp = client.post(f"/api/v1/cr/sessions/{ids['s1']}/reschedule",
                       json={"start_time": "09:00", "end_time": "11:00", "day_of_week": 3,
                             "venue": "Room B", "reason": "lecturer away",
                             "week": THIS_WEEK.isoformat()},
                       headers=_csrf(csrf))
    assert resp.status_code == 200, resp.text

    [moved] = _public(client, ids["cohort"], THIS_WEEK)
    assert (moved["day_of_week"], moved["start_time"], moved["venue"]) == (3, "09:00:00", "Room B")
    assert moved["rescheduled"] is True
    assert moved["reschedule_reason"] == "lecturer away"
    assert (moved["original_day_of_week"], moved["original_start_time"], moved["original_venue"]) == (
        1, "08:00:00", "Room A")

    [normal] = _public(client, ids["cohort"], NEXT_WEEK)
    assert (normal["day_of_week"], normal["start_time"], normal["venue"]) == (1, "08:00:00", "Room A")
    assert normal["rescheduled"] is False
    assert normal["original_day_of_week"] is None

    db = SessionLocal()
    try:
        row = db.get(TimetableSession, __import__("uuid").UUID(ids["s1"]))
        assert (row.day_of_week, row.start_time, row.venue_raw) == (1, time(8, 0), "Room A")
    finally:
        db.close()


def test_moving_back_to_published_slot_removes_the_override():
    ids = _seed()
    client = TestClient(app)
    csrf = _login(client)
    client.post(f"/api/v1/cr/sessions/{ids['s1']}/reschedule",
                json={"start_time": "09:00", "end_time": "11:00", "day_of_week": 3},
                headers=_csrf(csrf))
    back = client.post(f"/api/v1/cr/sessions/{ids['s1']}/reschedule",
                       json={"start_time": "08:00", "end_time": "10:00", "day_of_week": 1},
                       headers=_csrf(csrf))
    assert back.json()["rescheduled"] is False
    assert _occurrences() == []


def test_swap_applies_only_to_that_week():
    ids = _seed()
    s3 = _add_session(ids["cohort"], day=3, start=time(10, 0), end=time(12, 0), venue_code="Room B")
    client = TestClient(app)
    csrf = _login(client)
    resp = client.post(f"/api/v1/cr/sessions/{ids['s1']}/swap",
                       json={"with_session_id": s3, "week": THIS_WEEK.isoformat()},
                       headers=_csrf(csrf))
    assert resp.status_code == 200, resp.text

    this_week = {s["id"]: s for s in _public(client, ids["cohort"], THIS_WEEK)}
    assert this_week[ids["s1"]]["day_of_week"] == 3
    assert this_week[s3]["day_of_week"] == 1
    next_week = {s["id"]: s for s in _public(client, ids["cohort"], NEXT_WEEK)}
    assert next_week[ids["s1"]]["day_of_week"] == 1
    assert next_week[s3]["day_of_week"] == 3


def test_availability_follows_the_weeks_changes():
    ids = _seed()
    client = TestClient(app)
    csrf = _login(client)
    params = {"day": 1, "start": "08:00", "end": "10:00"}

    def free(week: date) -> dict[str, bool]:
        avail = client.get("/api/v1/cr/availability", params={**params, "week": week.isoformat()}).json()
        return {v["venue"]: v["free"] for v in avail["venues"]}

    assert free(THIS_WEEK)["Room A"] is False

    # Not held this week -> Room A is free this week only.
    client.post(f"/api/v1/cr/sessions/{ids['s1']}/live",
                json={"status": "not_held", "week": THIS_WEEK.isoformat()}, headers=_csrf(csrf))
    assert free(THIS_WEEK)["Room A"] is True
    assert free(NEXT_WEEK)["Room A"] is False

    # Next week the class moves to Room B at the same time: A frees up, B is taken.
    client.post(f"/api/v1/cr/sessions/{ids['s1']}/reschedule",
                json={"start_time": "08:00", "end_time": "10:00", "venue": "Room B",
                      "week": NEXT_WEEK.isoformat()}, headers=_csrf(csrf))
    nxt = free(NEXT_WEEK)
    assert nxt["Room A"] is True
    assert nxt["Room B"] is False


def test_venue_notice_applies_to_its_week_only():
    _seed()
    client = TestClient(app)
    csrf = _login(client)
    resp = client.post("/api/v1/cr/venue-notices",
                       json={"venue": "Room B", "day_of_week": 1, "start_time": "12:00",
                             "week": THIS_WEEK.isoformat()},
                       headers=_csrf(csrf))
    assert resp.status_code == 200, resp.text

    def notices(week: date) -> list[dict]:
        return client.get("/api/v1/venue-notices",
                          params={"day": 1, "week": week.isoformat()}).json()["notices"]

    [n] = notices(THIS_WEEK)
    assert n["week_start"] == THIS_WEEK.isoformat()
    assert notices(NEXT_WEEK) == []


def test_calendar_export_cancels_only_that_weeks_class():
    ids = _seed()
    client = TestClient(app)
    csrf = _login(client)
    client.post(f"/api/v1/cr/sessions/{ids['s1']}/live",
                json={"status": "not_held", "week": THIS_WEEK.isoformat()}, headers=_csrf(csrf))
    ics = client.get("/api/v1/timetable/export.ics", params={"cohort_code": ids["cohort"]}).text
    assert "RRULE:FREQ=WEEKLY;BYDAY=MO" in ics
    recurrence = f"RECURRENCE-ID;TZID=Africa/Dar_es_Salaam:{THIS_WEEK.strftime('%Y%m%d')}T080000"
    assert recurrence in ics
    assert "STATUS:CANCELLED" in ics


def test_this_weeks_changes_follow_the_class_to_a_newly_published_version():
    ids = _seed()
    client = TestClient(app)
    csrf = _login(client)
    client.post(f"/api/v1/cr/sessions/{ids['s1']}/live",
                json={"status": "not_held", "week": THIS_WEEK.isoformat()}, headers=_csrf(csrf))

    # A re-import of the same timetable as a new version under review.
    db = SessionLocal()
    try:
        old = db.execute(select(TimetableVersion)).scalar_one()
        src = db.execute(select(SourceDocument)).scalar_one()
        new = TimetableVersion(period_id=old.period_id, source_document_id=src.id, label="v2",
                               status=VersionStatus.review, is_active=False)
        db.add(new)
        db.flush()
        tpl = db.get(TimetableSession, __import__("uuid").UUID(ids["s1"]))
        copy = TimetableSession(version_id=new.id, day_of_week=tpl.day_of_week,
                                start_time=tpl.start_time, end_time=tpl.end_time,
                                course_id=tpl.course_id, course_name_raw=tpl.course_name_raw,
                                course_code_raw=tpl.course_code_raw, venue_id=tpl.venue_id,
                                venue_raw=tpl.venue_raw, source_page=tpl.source_page,
                                source_text_raw="raw", confidence="high")
        db.add(copy)
        db.flush()
        for link in db.execute(select(SessionCohort).where(SessionCohort.session_id == tpl.id)).scalars():
            db.add(SessionCohort(session_id=copy.id, cohort_id=link.cohort_id))
        db.commit()
        publish(db, new.id)
        db.commit()
        new_id = str(copy.id)
    finally:
        db.close()

    [s] = _public(client, ids["cohort"], THIS_WEEK)
    assert s["id"] == new_id
    assert s["live_status"] == "not_held"
