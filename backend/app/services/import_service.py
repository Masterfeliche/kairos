"""Import pipeline: source PDF -> draft timetable version (staging).

The whole import runs in **one transaction**. If anything fails, the transaction is
rolled back and the database is left exactly as it was (no partial version, no orphan
sessions) — see docs/05-system-architecture.md §6.3 and the Phase 2 DoD.

Extraction writes **staging only** (a `draft`/`review` version). It can never publish.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import atomic
from app.extraction import (
    lecturer_parts,
    normalise,
    parse_pdf,
    validate_session,
)
from app.extraction.parser import DAYS  # noqa: F401  (re-exported for callers)
from app.models import (
    AcademicPeriod,
    Cohort,
    Confidence,
    Course,
    ExtractionMethod,
    ImportJob,
    Institution,
    IssueSeverity,
    JobStatus,
    Lecturer,
    Programme,
    ProgrammeLevel,
    Semester,
    SessionCohort,
    SessionFieldEvidence,
    SessionLecturer,
    SessionType,
    SourceDocument,
    TimetableSession,
    TimetableVersion,
    ValidationIssue,
    Venue,
    VersionStatus,
)

INSTITUTION_CODE = "DIT"
INSTITUTION_NAME = "Dar es Salaam Institute of Technology"

_PROG_RE = re.compile(r"^(?P<prog>[A-Z]+)\d{2}")


@dataclass
class ImportSummary:
    version_id: uuid.UUID
    sessions: int
    with_code: int
    issues: int
    errors: int
    warnings: int


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def infer_programme(cohort_code: str) -> tuple[str, str, ProgrammeLevel]:
    """Derive a stable programme from a cohort code. Reversible, best-effort."""
    code = cohort_code.upper()
    prog = None
    m = _PROG_RE.match(code)
    if m:
        prog = m.group("prog")
    elif code.startswith("MASTERS"):
        return ("MASTERS (Postgraduate)", "MASTERS", ProgrammeLevel.masters)
    elif code.startswith("MT") or code.startswith("MC"):
        return ("MASTERS (Postgraduate)", "MASTERS", ProgrammeLevel.masters)

    if prog is None:
        prog = code.split("-")[0][:8] or "UNKNOWN"

    if prog.startswith("BENG"):
        level = ProgrammeLevel.beng
    elif prog.startswith("BT"):
        level = ProgrammeLevel.btech
    elif prog.startswith("OD"):
        level = ProgrammeLevel.diploma
    else:
        level = ProgrammeLevel.diploma
    return (prog, prog, level)


def _parse_intake(cohort_code: str) -> int | None:
    m = re.search(r"(\d{2})", cohort_code)
    return 2000 + int(m.group(1)) if m else None


def _section(cohort_code: str) -> str | None:
    m = re.search(r"-(\d+)$", cohort_code)
    return m.group(1) if m else None


def get_or_create(session: Session, model, defaults: dict | None = None, **filters):
    obj = session.execute(select(model).filter_by(**filters)).scalar_one_or_none()
    if obj is not None:
        return obj, False
    obj = model(**filters, **(defaults or {}))
    session.add(obj)
    session.flush()
    return obj, True


def _store_source(pdf_path: Path, sha: str) -> str:
    dest_dir = Path(settings.storage_dir) / "sources"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{sha}.pdf"
    if not dest.exists():
        shutil.copy2(pdf_path, dest)
    return str(dest.relative_to(Path(settings.storage_dir)))


def import_pdf(
    session: Session,
    pdf_path: str | Path,
    *,
    original_filename: str | None = None,
    year_label: str = "2025/2026",
    semester: Semester = Semester.s1,
    label: str = "Semester I",
) -> ImportSummary:
    """Run the full import in a single transaction. Raises on failure (DB unchanged)."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)
    if pdf_path.read_bytes()[:5] != b"%PDF-":
        raise ValueError("Not a PDF (missing %PDF- magic bytes).")

    original_filename = original_filename or pdf_path.name
    sha = _sha256(pdf_path)

    with atomic(session):
        institution, _ = get_or_create(
            session, Institution, code=INSTITUTION_CODE, defaults={"name": INSTITUTION_NAME}
        )
        period, _ = get_or_create(
            session,
            AcademicPeriod,
            institution_id=institution.id,
            year_label=year_label,
            semester=semester,
            defaults={"is_active": True},
        )

        # Parse before creating rows so a parse crash touches nothing.
        parsed = parse_pdf(pdf_path)
        page_count = max((s.page for s in parsed), default=0)

        storage_key = _store_source(pdf_path, sha)
        source, source_created = get_or_create(
            session,
            SourceDocument,
            sha256=sha,
            defaults={
                "period_id": period.id,
                "original_filename": original_filename,
                "page_count": page_count,
                "storage_key": storage_key,
            },
        )
        if not source_created and original_filename:
            source.original_filename = original_filename

        version = TimetableVersion(
            period_id=period.id,
            source_document_id=source.id,
            label=label,
            status=VersionStatus.draft,
            is_active=False,
        )
        session.add(version)
        session.flush()

        job = ImportJob(
            version_id=version.id,
            source_document_id=source.id,
            status=JobStatus.running,
            started_at=_now(),
        )
        session.add(job)
        session.flush()

        course_by_code: dict[str, Course] = {}
        venue_by_code: dict[str, Venue] = {}
        lecturer_by_name: dict[str, Lecturer] = {}

        n_errors = n_warnings = 0

        for ps in parsed:
            norm = normalise(ps)

            # --- course ------------------------------------------------------
            course = None
            if norm["course_code_raw"]:
                code = norm["course_code_raw"]
                course = course_by_code.get(code)
                if course is None:
                    course, _ = get_or_create(
                        session,
                        Course,
                        code=code,
                        defaults={"name": norm["course_name_raw"] or code,
                                  "department": norm["department"]},
                    )
                    course_by_code[code] = course

            # --- venue -------------------------------------------------------
            venue = None
            if norm["venue_raw"]:
                key = norm["venue_raw"].upper()
                venue = venue_by_code.get(key)
                if venue is None:
                    venue, _ = get_or_create(session, Venue, code=norm["venue_raw"])
                    venue_by_code[key] = venue

            tsession = TimetableSession(
                version_id=version.id,
                day_of_week=norm["day_of_week"] or 0,
                start_time=norm["start_time"],
                end_time=norm["end_time"],
                course_id=course.id if course else None,
                course_name_raw=norm["course_name_raw"],
                course_code_raw=norm["course_code_raw"],
                venue_id=venue.id if venue else None,
                venue_raw=norm["venue_raw"],
                lecturer_raw=norm["lecturer_raw"],
                session_type=SessionType(norm["session_type"]) if norm["session_type"] else None,
                extraction_method=ExtractionMethod.geometry,
                confidence=Confidence(norm["confidence"]),
                source_page=norm["source_page"],
                source_cell_bbox=str(norm["source_cell_bbox"]),
                source_text_raw=norm["source_text_raw"],
                is_shared=norm["is_shared"],
            )
            session.add(tsession)
            session.flush()

            # --- cohorts (shared sessions => many-to-many) -------------------
            for i, raw_code in enumerate(norm["cohort_codes"]):
                prog_name, prog_code, level = infer_programme(raw_code)
                programme, _ = get_or_create(
                    session, Programme, code=prog_code,
                    defaults={"institution_id": institution.id, "name": prog_name,
                              "level": level, "department": norm["department"]},
                )
                cohort, _ = get_or_create(
                    session, Cohort, code=raw_code,
                    defaults={"programme_id": programme.id, "intake_year": _parse_intake(raw_code),
                              "section": _section(raw_code)},
                )
                session.add(SessionCohort(session_id=tsession.id, cohort_id=cohort.id,
                                          is_primary=(i == 0)))

            # --- lecturers ---------------------------------------------------
            for name in lecturer_parts(norm["lecturer_raw"]):
                lecturer = lecturer_by_name.get(name)
                if lecturer is None:
                    lecturer, _ = get_or_create(session, Lecturer, name=name)
                    lecturer_by_name[name] = lecturer
                session.add(SessionLecturer(session_id=tsession.id, lecturer_id=lecturer.id,
                                            raw_name=name))

            # --- validation issues ------------------------------------------
            for issue in validate_session(norm):
                session.add(ValidationIssue(version_id=version.id, session_id=tsession.id,
                                            code=issue["code"], severity=issue["severity"],
                                            message=issue["message"], page=issue["page"]))
                if issue["severity"] == IssueSeverity.error:
                    n_errors += 1
                elif issue["severity"] == IssueSeverity.warning:
                    n_warnings += 1

            # --- field evidence for uncertainty ------------------------------
            for reason in norm["reasons"]:
                session.add(SessionFieldEvidence(session_id=tsession.id, field_name="course_code_raw",
                                                 value=None, confidence=Confidence.low, reason=reason))

        with_code = sum(1 for s in parsed if s.course_code)
        version.status = VersionStatus.review
        job.status = JobStatus.succeeded
        job.progress = 100
        job.finished_at = _now()
        job.summary = (
            f'{{"sessions": {len(parsed)}, "with_code": {with_code}, '
            f'"errors": {n_errors}, "warnings": {n_warnings}}}'
        )

        return ImportSummary(
            version_id=version.id,
            sessions=len(parsed),
            with_code=with_code,
            issues=n_errors + n_warnings,
            errors=n_errors,
            warnings=n_warnings,
        )
