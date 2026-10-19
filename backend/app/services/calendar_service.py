"""iCalendar (.ics) generation for cohort timetables (RFC 5545)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

DAY_BYDAY = {
    1: "MO",
    2: "TU",
    3: "WE",
    4: "TH",
    5: "FR",
    6: "SA",
    7: "SU",
}


def _clean_text(s: str | None) -> str:
    if not s:
        return ""
    # Escape backslashes, semicolons, commas, and newlines for iCalendar
    return (
        s.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .strip()
    )


def _monday_of_current_week(ref_date: date | None = None) -> date:
    if ref_date is None:
        from app.core.campus import current_week_start

        return current_week_start()
    return ref_date - timedelta(days=ref_date.weekday())


def _local(d: date, hhmm: str) -> str:
    h, m = [int(p) for p in hhmm.split(":")[:2]]
    return f"{d.strftime('%Y%m%d')}T{h:02d}{m:02d}00"


def generate_cohort_ics(
    cohort_code: str,
    sessions: list[dict],
    *,
    version_label: str = "Semester I",
    weeks_count: int = 16,
    start_monday: date | None = None,
    overrides: dict[str, list[dict]] | None = None,
) -> str:
    """Generate an RFC 5545 iCalendar string for a cohort timetable.

    Each session is a weekly recurring event in its published slot. ``overrides`` maps a
    session id to that session's class-rep changes for specific weeks (``week_start``,
    ``not_held``, ``moved`` and the effective slot); each becomes an override instance
    (``RECURRENCE-ID``) so calendars show the cancellation or move for that week only.
    """
    overrides = overrides or {}
    monday = start_monday or _monday_of_current_week()
    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//DIT Smart Timetable//Teaching Timetable//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:DIT {cohort_code} Timetable",
        "X-WR-TIMEZONE:Africa/Dar_es_Salaam",
        "BEGIN:VTIMEZONE",
        "TZID:Africa/Dar_es_Salaam",
        "X-LIC-LOCATION:Africa/Dar_es_Salaam",
        "BEGIN:STANDARD",
        "TZOFFSETFROM:+0300",
        "TZOFFSETTO:+0300",
        "TZNAME:EAT",
        "DTSTART:19700101T000000",
        "END:STANDARD",
        "END:VTIMEZONE",
    ]

    for s in sessions:
        day_of_week = s.get("day_of_week")
        if not day_of_week or day_of_week not in DAY_BYDAY:
            continue
        start_time_str = s.get("start_time")
        end_time_str = s.get("end_time")
        if not start_time_str or not end_time_str:
            continue

        sh, sm = [int(p) for p in start_time_str.split(":")[:2]]
        eh, em = [int(p) for p in end_time_str.split(":")[:2]]

        session_date = monday + timedelta(days=day_of_week - 1)
        dtstart = f"{session_date.strftime('%Y%m%d')}T{sh:02d}{sm:02d}00"
        dtend = f"{session_date.strftime('%Y%m%d')}T{eh:02d}{em:02d}00"

        course_code = s.get("course_code")
        course_name = s.get("course_name") or "Lecture"
        summary = f"{course_name} ({course_code})" if course_code else course_name

        venue = s.get("venue") or "DIT Campus"
        lecturers = s.get("lecturers") or []
        lecturer_str = ", ".join(lecturers) if lecturers else "Not specified"
        dept = s.get("department") or ""

        desc_parts = [f"Class: {cohort_code}"]
        if course_code:
            desc_parts.append(f"Course Code: {course_code}")
        if dept:
            desc_parts.append(f"Department: {dept}")
        desc_parts.append(f"Lecturer(s): {lecturer_str}")
        if venue:
            desc_parts.append(f"Venue: {venue}")
        shared_with = s.get("shared_with") or []
        if shared_with:
            desc_parts.append(f"Shared with: {', '.join(shared_with)}")
        desc_parts.append(f"Source: DIT {version_label}")

        description = "\\n".join(_clean_text(p) for p in desc_parts)
        byday = DAY_BYDAY[day_of_week]
        uid = f"{s.get('id', 'sess')}@{cohort_code.lower()}.dit.ac.tz"

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_utc}",
            f"DTSTART;TZID=Africa/Dar_es_Salaam:{dtstart}",
            f"DTEND;TZID=Africa/Dar_es_Salaam:{dtend}",
            f"RRULE:FREQ=WEEKLY;BYDAY={byday};COUNT={weeks_count}",
            f"SUMMARY:{_clean_text(summary)}",
            f"LOCATION:{_clean_text(venue)}",
            f"DESCRIPTION:{description}",
            "STATUS:CONFIRMED",
            "END:VEVENT",
        ])

        for ov in overrides.get(str(s.get("id")), []):
            if not (ov.get("not_held") or ov.get("moved")):
                continue
            occ_date = ov["week_start"] + timedelta(days=day_of_week - 1)
            recurrence_id = _local(occ_date, start_time_str)
            if ov.get("not_held"):
                ov_start, ov_end, ov_venue = recurrence_id, _local(occ_date, end_time_str), venue
                ov_summary, ov_status = f"Not held: {summary}", "CANCELLED"
            else:
                moved_date = ov["week_start"] + timedelta(days=ov["day_of_week"] - 1)
                ov_start = _local(moved_date, ov["start_time"])
                ov_end = _local(moved_date, ov["end_time"])
                ov_venue = ov.get("venue") or venue
                ov_summary, ov_status = f"Moved: {summary}", "CONFIRMED"
            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now_utc}",
                f"RECURRENCE-ID;TZID=Africa/Dar_es_Salaam:{recurrence_id}",
                f"DTSTART;TZID=Africa/Dar_es_Salaam:{ov_start}",
                f"DTEND;TZID=Africa/Dar_es_Salaam:{ov_end}",
                f"SUMMARY:{_clean_text(ov_summary)}",
                f"LOCATION:{_clean_text(ov_venue)}",
                f"DESCRIPTION:{description}",
                f"STATUS:{ov_status}",
                "END:VEVENT",
            ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
