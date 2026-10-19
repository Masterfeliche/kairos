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
    d = ref_date or date.today()
    return d - timedelta(days=d.weekday())


def generate_cohort_ics(
    cohort_code: str,
    sessions: list[dict],
    *,
    version_label: str = "Semester I",
    weeks_count: int = 16,
    start_monday: date | None = None,
) -> str:
    """Generate an RFC 5545 iCalendar string for a cohort timetable."""
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

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
