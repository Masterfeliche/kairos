"""Campus calendar helpers.

The timetable is a weekly template in East Africa Time (UTC+3, no daylight saving).
Operational changes made by class representatives apply to one *teaching week*,
identified by its Monday. At weekends the "current" week is the coming one, matching
what the student site shows.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

CAMPUS_TZ = timezone(timedelta(hours=3), name="EAT")


def campus_today(now: datetime | None = None) -> date:
    now = now or datetime.now(timezone.utc)
    return now.astimezone(CAMPUS_TZ).date()


def week_start(d: date) -> date:
    """Monday of the week containing ``d``."""
    return d - timedelta(days=d.weekday())


def current_week_start(now: datetime | None = None) -> date:
    """Monday of the teaching week shown as "this week" (the coming week at weekends)."""
    today = campus_today(now)
    monday = week_start(today)
    return monday + timedelta(days=7) if today.weekday() >= 5 else monday


def resolve_week(value: date | None, now: datetime | None = None) -> date:
    """Normalise an optional date (any day of a week) to that week's Monday."""
    return week_start(value) if value is not None else current_week_start(now)
