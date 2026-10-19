"""Validation: turn normalised sessions into reviewable issues.

Severity guide:
  - error   : blocks publish (e.g. missing course code, missing day/time)
  - warning : publishable but needs a look (e.g. unparsed venue, shared session)
  - info    : FYI (e.g. multi-hour block detected)
"""
from __future__ import annotations

from app.models import IssueSeverity


def validate_session(normalised: dict) -> list[dict]:
    issues: list[dict] = []

    if not normalised.get("course_code_raw"):
        issues.append(
            {
                "code": "MISSING_CODE",
                "severity": IssueSeverity.error,
                "message": f"No course code parsed from cell: {normalised.get('source_text_raw', '')[:80]!r}",
                "page": normalised.get("source_page"),
            }
        )
    if normalised.get("day_of_week") is None:
        issues.append({"code": "MISSING_DAY", "severity": IssueSeverity.error,
                       "message": "Could not map column to a weekday.",
                       "page": normalised.get("source_page")})
    if not normalised.get("start_time") or not normalised.get("end_time"):
        issues.append({"code": "MISSING_TIME", "severity": IssueSeverity.error,
                       "message": "Could not derive start/end time.",
                       "page": normalised.get("source_page")})
    if normalised.get("venue_raw") is None and normalised.get("course_code_raw"):
        issues.append({"code": "VENUE_UNSPLIT", "severity": IssueSeverity.warning,
                       "message": "Venue could not be separated from the lecturer text.",
                       "page": normalised.get("source_page")})
    if normalised.get("is_shared"):
        issues.append({"code": "SHARED_SESSION", "severity": IssueSeverity.info,
                       "message": "Session belongs to multiple cohorts.",
                       "page": normalised.get("source_page")})
    if normalised.get("multi_hour"):
        issues.append({"code": "MULTI_HOUR", "severity": IssueSeverity.info,
                       "message": "Cell spans more than one hour (multi-hour block).",
                       "page": normalised.get("source_page")})
    if not normalised.get("cohort_codes"):
        issues.append({"code": "MISSING_COHORT", "severity": IssueSeverity.error,
                       "message": "No cohort identifier resolved for this session.",
                       "page": normalised.get("source_page")})
    return issues
