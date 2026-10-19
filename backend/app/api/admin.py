"""Admin API (docs/07-api-specification.md §8).

All endpoints require an authenticated admin. State-changing endpoints additionally
require a matching CSRF token; publish/rollback require the ``owner`` role. Every
mutation is written to the append-only audit trail (docs/08 §9.4).
"""
from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    client_ip,
    get_current_staff,
    require_owner,
    verify_csrf,
)
from app.core.config import settings
from app.core.db import atomic, get_session
from app.models import (
    AdminUser,
    Cohort,
    ImportJob,
    PublicationRecord,
    Semester,
    SessionCohort,
    SourceDocument,
    TimetableSession,
    TimetableVersion,
    ValidationIssue,
)
from app.schemas.timetable import ImportResult, VersionOut
from app.services import audit_record, import_pdf, publish, rollback
from app.services.correction_service import CorrectionError, apply_correction, resolve_issue
from app.services.diff_service import diff_versions
from app.services.publish_service import PublishError
from app.services.rendering import render_page_bytes

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

_BAD_PDF_TOKENS = (b"/JavaScript", b"/Launch", b"/Encrypt")


class CorrectionIn(BaseModel):
    changes: dict
    reason: str


def _source_path(source: SourceDocument) -> Path:
    path = Path(settings.storage_dir) / source.storage_key
    if not path.exists():
        raise HTTPException(status_code=404, detail="Source PDF not found in storage.")
    return path


# ---------------------------------------------------------------- imports -----
@router.post("/import", response_model=ImportResult)
def import_document(
    request: Request,
    file: UploadFile = File(...),
    year_label: str = Form("2025/2026"),
    semester: str = Form("1"),
    label: str = Form("Semester I"),
    force: bool = Form(False),
    db: Session = Depends(get_session),
    admin: AdminUser = Depends(get_current_staff),
    _csrf: None = Depends(verify_csrf),
):
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are accepted.")

    data = file.file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File too large.")
    if data[:5] != b"%PDF-":
        raise HTTPException(status_code=400, detail="Not a PDF (missing %PDF- magic bytes).")
    for token in _BAD_PDF_TOKENS:
        if token in data:
            raise HTTPException(status_code=400,
                                detail=f"PDF rejected: contains disallowed content ({token.decode()}).")

    import hashlib
    sha = hashlib.sha256(data).hexdigest()
    existing_source = db.execute(
        select(SourceDocument).where(SourceDocument.sha256 == sha)
    ).scalar_one_or_none()
    if existing_source is not None and not force:
        raise HTTPException(
            status_code=409,
            detail="This PDF was already imported (identical SHA-256). Re-submit with force=true.",
        )

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        summary = import_pdf(db, tmp_path, original_filename=file.filename,
                             year_label=year_label,
                             semester=Semester(semester), label=label)
    finally:
        tmp_path.unlink(missing_ok=True)

    with atomic(db):
        audit_record(db, actor=admin, action="import.create", entity_type="timetable_version",
                     entity_id=str(summary.version_id),
                     after={"sessions": summary.sessions, "errors": summary.errors,
                            "warnings": summary.warnings, "sha256": sha},
                     ip=client_ip(request))

    return ImportResult(
        version_id=str(summary.version_id), sessions=summary.sessions,
        with_code=summary.with_code, issues=summary.issues, errors=summary.errors,
        warnings=summary.warnings,
    )


# ---------------------------------------------------------------- versions ----
@router.get("/versions", response_model=list[VersionOut])
def list_versions(db: Session = Depends(get_session),
                  admin: AdminUser = Depends(get_current_staff)):
    return list(db.execute(
        select(TimetableVersion).order_by(TimetableVersion.created_at.desc())
    ).scalars())


@router.get("/versions/{version_id}")
def version_detail(version_id: uuid.UUID, db: Session = Depends(get_session),
                   admin: AdminUser = Depends(get_current_staff)):
    version = db.get(TimetableVersion, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found.")
    sessions = db.execute(
        select(func.count()).select_from(TimetableSession)
        .where(TimetableSession.version_id == version_id)
    ).scalar_one()
    unresolved = db.execute(
        select(func.count()).select_from(ValidationIssue)
        .where(ValidationIssue.version_id == version_id,
               ValidationIssue.resolved_at.is_(None))
    ).scalar_one()
    errors = db.execute(
        select(func.count()).select_from(ValidationIssue)
        .where(ValidationIssue.version_id == version_id,
               ValidationIssue.resolved_at.is_(None),
               ValidationIssue.severity == "error")
    ).scalar_one()
    source = db.get(SourceDocument, version.source_document_id)
    return {
        "id": str(version.id),
        "period_id": str(version.period_id),
        "label": version.label,
        "status": version.status.value,
        "is_active": version.is_active,
        "sessions": sessions,
        "open_issues": unresolved,
        "open_errors": errors,
        "pages": source.page_count if source else None,
        "source_document_id": str(version.source_document_id),
    }


@router.get("/versions/{version_id}/issues")
def version_issues(version_id: uuid.UUID, include_resolved: bool = False,
                   db: Session = Depends(get_session),
                   admin: AdminUser = Depends(get_current_staff)):
    stmt = select(ValidationIssue).where(ValidationIssue.version_id == version_id)
    if not include_resolved:
        stmt = stmt.where(ValidationIssue.resolved_at.is_(None))
    rows = db.execute(stmt).scalars().all()
    return [
        {"id": str(i.id), "session_id": str(i.session_id) if i.session_id else None,
         "code": i.code, "severity": i.severity.value, "message": i.message,
         "page": i.page, "resolved": i.resolved_at is not None}
        for i in rows
    ]


@router.get("/versions/{version_id}/sessions")
def version_sessions(
    version_id: uuid.UUID,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    q: str | None = None,
    only_issues: bool = False,
    db: Session = Depends(get_session),
    admin: AdminUser = Depends(get_current_staff),
):
    stmt = select(TimetableSession).where(TimetableSession.version_id == version_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            TimetableSession.course_code_raw.ilike(like)
            | TimetableSession.course_name_raw.ilike(like)
            | TimetableSession.lecturer_raw.ilike(like)
            | TimetableSession.venue_raw.ilike(like)
        )
    if only_issues:
        sub = select(ValidationIssue.session_id).where(
            ValidationIssue.version_id == version_id,
            ValidationIssue.resolved_at.is_(None),
            ValidationIssue.session_id.is_not(None),
        )
        stmt = stmt.where(TimetableSession.id.in_(sub))

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    stmt = stmt.order_by(TimetableSession.source_page, TimetableSession.day_of_week,
                         TimetableSession.start_time).offset((page - 1) * size).limit(size)
    rows = db.execute(stmt).scalars().all()

    cohort_map: dict = {}
    if rows:
        links = db.execute(
            select(SessionCohort.session_id, Cohort.code)
            .join(Cohort, Cohort.id == SessionCohort.cohort_id)
            .where(SessionCohort.session_id.in_([r.id for r in rows]))
        ).all()
        for sid, code in links:
            cohort_map.setdefault(sid, []).append(code)

    items = []
    for s in rows:
        items.append({
            "id": str(s.id),
            "day_of_week": s.day_of_week,
            "start_time": s.start_time.isoformat(),
            "end_time": s.end_time.isoformat(),
            "course_code_raw": s.course_code_raw,
            "course_name_raw": s.course_name_raw,
            "lecturer_raw": s.lecturer_raw,
            "venue_raw": s.venue_raw,
            "session_type": s.session_type.value if s.session_type else None,
            "cohort_codes": sorted(cohort_map.get(s.id, [])),
            "confidence": s.confidence.value,
            "extraction_method": s.extraction_method.value,
            "source_page": s.source_page,
            "is_shared": s.is_shared,
        })
    return {"total": total, "page": page, "size": size, "items": items}


@router.post("/sessions/{session_id}/correct")
def correct_session(session_id: uuid.UUID, body: CorrectionIn,
                    db: Session = Depends(get_session),
                    admin: AdminUser = Depends(get_current_staff),
                    _csrf: None = Depends(verify_csrf)):
    try:
        with atomic(db):
            ts = apply_correction(db, session_id=session_id, changes=body.changes,
                                  reason=body.reason, actor=admin)
    except CorrectionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": str(ts.id), "ok": True}


@router.post("/issues/{issue_id}/resolve")
def resolve_issue_endpoint(issue_id: uuid.UUID, db: Session = Depends(get_session),
                           admin: AdminUser = Depends(get_current_staff),
                           _csrf: None = Depends(verify_csrf)):
    try:
        with atomic(db):
            issue = resolve_issue(db, issue_id=issue_id, actor=admin)
    except CorrectionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"id": str(issue.id), "resolved": True}


@router.get("/versions/{version_id}/diff")
def version_diff(version_id: uuid.UUID, base: uuid.UUID | None = None,
                 db: Session = Depends(get_session),
                 admin: AdminUser = Depends(get_current_staff)):
    try:
        return diff_versions(db, version_id, base)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/versions/{version_id}/pages/{page}.png")
def version_page_image(version_id: uuid.UUID, page: int,
                       db: Session = Depends(get_session),
                       admin: AdminUser = Depends(get_current_staff)):
    version = db.get(TimetableVersion, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found.")
    source = db.get(SourceDocument, version.source_document_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source document not found.")
    try:
        png = render_page_bytes(_source_path(source), page)
    except IndexError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(content=png, media_type="image/png",
                    headers={"Cache-Control": "private, max-age=3600"})


# ------------------------------------------------------------ publish/rollback -
@router.post("/versions/{version_id}/publish", response_model=VersionOut)
def publish_version(version_id: uuid.UUID, db: Session = Depends(get_session),
                    admin: AdminUser = Depends(require_owner),
                    _csrf: None = Depends(verify_csrf)):
    try:
        with atomic(db):
            summary = diff_versions(db, version_id)
            publish(db, version_id)
            audit_record(db, actor=admin, action="version.publish",
                         entity_type="timetable_version", entity_id=str(version_id),
                         after=summary["summary"])
    except PublishError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return db.get(TimetableVersion, version_id)


@router.post("/periods/{period_id}/rollback/{version_id}", response_model=VersionOut)
def rollback_version(period_id: uuid.UUID, version_id: uuid.UUID,
                     db: Session = Depends(get_session),
                     admin: AdminUser = Depends(require_owner),
                     _csrf: None = Depends(verify_csrf)):
    try:
        with atomic(db):
            rollback(db, period_id, version_id)
            audit_record(db, actor=admin, action="version.rollback",
                         entity_type="timetable_version", entity_id=str(version_id),
                         after={"period_id": str(period_id)})
    except PublishError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return db.get(TimetableVersion, version_id)


# ---------------------------------------------------------------- history -----
@router.get("/jobs")
def list_jobs(db: Session = Depends(get_session),
              admin: AdminUser = Depends(get_current_staff)):
    rows = db.execute(select(ImportJob).order_by(ImportJob.started_at.desc())).scalars()
    return [
        {"id": str(j.id), "version_id": str(j.version_id), "status": j.status.value,
         "progress": j.progress, "summary": j.summary,
         "started_at": j.started_at.isoformat() if j.started_at else None,
         "finished_at": j.finished_at.isoformat() if j.finished_at else None}
        for j in rows
    ]


@router.get("/history")
def list_history(db: Session = Depends(get_session),
                 admin: AdminUser = Depends(get_current_staff)):
    rows = db.execute(
        select(PublicationRecord, TimetableVersion.label)
        .join(TimetableVersion, TimetableVersion.id == PublicationRecord.version_id)
        .order_by(PublicationRecord.published_at.desc())
    ).all()
    return [
        {"id": str(r.id), "version_id": str(r.version_id), "label": label,
         "action": r.action.value,
         "published_at": r.published_at.isoformat() if r.published_at else None,
         "previous_version_id": str(r.previous_version_id) if r.previous_version_id else None,
         "diff_summary": r.diff_summary}
        for r, label in rows
    ]


@router.get("/audit")
def list_audit(limit: int = Query(100, ge=1, le=500),
               db: Session = Depends(get_session),
               admin: AdminUser = Depends(get_current_staff)):
    from app.models import AuditEvent
    rows = db.execute(
        select(AuditEvent, AdminUser.email)
        .outerjoin(AdminUser, AdminUser.id == AuditEvent.actor_id)
        .order_by(AuditEvent.at.desc()).limit(limit)
    ).all()
    return [
        {"id": str(e.id), "at": e.at.isoformat() if e.at else None,
         "actor": email, "action": e.action, "entity_type": e.entity_type,
         "entity_id": e.entity_id, "before": e.before, "after": e.after, "ip": e.ip}
        for e, email in rows
    ]


@router.get("/source-documents")
def list_sources(db: Session = Depends(get_session),
                 admin: AdminUser = Depends(get_current_staff)):
    rows = db.execute(select(SourceDocument)).scalars()
    return [
        {"id": str(s.id), "filename": s.original_filename, "sha256": s.sha256,
         "page_count": s.page_count, "uploaded_at": s.uploaded_at.isoformat()}
        for s in rows
    ]
