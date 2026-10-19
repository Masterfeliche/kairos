"""Tests for RFC 5545 iCalendar generation."""
from __future__ import annotations

from datetime import date
from app.services.calendar_service import generate_cohort_ics, _clean_text


def test_clean_text():
    assert _clean_text("Hello, World; Test\\Path") == "Hello\\, World\\; Test\\\\Path"
    assert _clean_text("Line 1\nLine 2") == "Line 1\\nLine 2"
    assert _clean_text(None) == ""


def test_generate_cohort_ics_structure():
    sessions = [
        {
            "id": "test-uuid-1",
            "day_of_week": 1,
            "start_time": "08:00:00",
            "end_time": "10:00:00",
            "course_name": "Web Programming",
            "course_code": "CS 101",
            "venue": "Lab 4",
            "lecturers": ["Dr. Smith"],
            "department": "CS",
            "shared_with": ["OD24COE-2"],
        },
        {
            "id": "test-uuid-2",
            "day_of_week": 3,
            "start_time": "14:00:00",
            "end_time": "16:00:00",
            "course_name": "Database Systems",
            "course_code": "CS 102",
            "venue": "Lecture Room 1",
            "lecturers": [],
        },
    ]

    ics = generate_cohort_ics(
        "OD24COE-1",
        sessions,
        version_label="Semester I",
        start_monday=date(2026, 10, 19),
    )

    assert "BEGIN:VCALENDAR" in ics
    assert "VERSION:2.0" in ics
    assert "X-WR-CALNAME:DIT OD24COE-1 Timetable" in ics
    assert "BEGIN:VTIMEZONE" in ics
    assert "TZID:Africa/Dar_es_Salaam" in ics

    # Event 1 checks
    assert "BEGIN:VEVENT" in ics
    assert "UID:test-uuid-1@od24coe-1.dit.ac.tz" in ics
    assert "DTSTART;TZID=Africa/Dar_es_Salaam:20261019T080000" in ics
    assert "DTEND;TZID=Africa/Dar_es_Salaam:20261019T100000" in ics
    assert "RRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=16" in ics
    assert "SUMMARY:Web Programming (CS 101)" in ics
    assert "LOCATION:Lab 4" in ics
    assert "Lecturer(s): Dr. Smith" in ics
    assert "Shared with: OD24COE-2" in ics

    # Event 2 checks
    assert "UID:test-uuid-2@od24coe-1.dit.ac.tz" in ics
    assert "DTSTART;TZID=Africa/Dar_es_Salaam:20261021T140000" in ics
    assert "DTEND;TZID=Africa/Dar_es_Salaam:20261021T160000" in ics
    assert "RRULE:FREQ=WEEKLY;BYDAY=WE;COUNT=16" in ics
    assert "SUMMARY:Database Systems (CS 102)" in ics

    assert "END:VCALENDAR" in ics
