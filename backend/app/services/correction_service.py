"""Admin corrections to extracted sessions (docs/06-ux-specification.md A1, docs/09 §9.4)."""
from __future__ import annotations

import json
from datetime import datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AdminUser,
    Confidence,
    Course,
    ExtractionMethod,
    SessionFieldEvidence,
    SessionType,
    TimetableSession,
    ValidationIssue,
)
from app.services import audit_service

EDITABLE = {
    "course_code_raw", "course_name_raw", "lecturer_raw", "venue_raw",
    "session_type", "day_of_week", "start_time", "end_time",
}


class CorrectionError(Exception):
    pass


def _coerce(field: str, value):
    if field in ("start_time", "end_time"):
        if value is None:
            return None
        if isinstance(value, time):
            return value
        return time.fromisoformat(str(value))
    if field == "day_of_week":
        return int(value) if value is not None else None
    if field == "session_type":
        return SessionType(value) if value else None
    return value


def apply_correction(
    session: Session,
    *,
    session_id,
    changes: dict,
    reason: str,
    actor: AdminUser | None,
    ip: str | None = None,
) -> TimetableSession:
    ts = session.get(TimetableSession, session_id)
    if ts is None:
        raise CorrectionError("Session not found.")
    if not reason or not reason.strip():
        raise CorrectionError("A reason is required for every correction.")

    unknown = set(changes) - EDITABLE
    if unknown:
        raise CorrectionError(f"Fields not editable: {', '.join(sorted(unknown))}")

    before = {f: str(getattr(ts, f)) for f in changes}
    after: dict = {}
    for field, value in changes.items():
        setattr(ts, field, _coerce(field, value))
        after[field] = str(getattr(ts, field))
    ts.extraction_method = ExtractionMethod.manual

    # If a code was supplied, clear the corresponding blocking issue.
    if changes.get("course_code_raw"):
        open_issue = session.execute(
            select(ValidationIssue).where(
                ValidationIssue.session_id == ts.id,
                ValidationIssue.code == "MISSING_CODE",
                ValidationIssue.resolved_at.is_(None),
            )
        ).scalars().first()
        if open_issue is not None:
            open_issue.resolved_at = datetime.utcnow()

    for field in changes:
        session.add(SessionFieldEvidence(
            session_id=ts.id, field_name=field, value=str(getattr(ts, field)),
            confidence=Confidence.high, reason=f"manual: {reason}",
        ))

    audit_service.record(
        session, actor=actor, action="session.correct", entity_type="timetable_session",
        entity_id=str(ts.id), before=json.loads(json.dumps(before)),
        after=after, ip=ip,
    )
    session.flush()
    return ts


def resolve_issue(session: Session, *, issue_id, actor: AdminUser | None,
                  reason: str | None = None, ip: str | None = None) -> ValidationIssue:
    issue = session.get(ValidationIssue, issue_id)
    if issue is None:
        raise CorrectionError("Issue not found.")
    issue.resolved_at = datetime.utcnow()
    audit_service.record(
        session, actor=actor, action="issue.resolve", entity_type="validation_issue",
        entity_id=str(issue.id), before={"code": issue.code, "resolved": False},
        after={"code": issue.code, "resolved": True, "reason": reason}, ip=ip,
    )
    session.flush()
    return issue
