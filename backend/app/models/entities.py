"""ORM entities for the MVP (see docs/04-data-model.md).

Deliberately implemented with portable SQLAlchemy types so the same models run on
SQLite (dev/tests) and PostgreSQL (production). PostgreSQL-specific partial unique
indexes are expressed with ``postgresql_where`` and degrade gracefully on SQLite
using ``sqlite_where``.
"""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, utcnow


def _enum(py_enum, name: str) -> Enum:
    return Enum(py_enum, name=name, native_enum=False, validate_strings=True)


class ProgrammeLevel(str, enum.Enum):
    beng = "beng"
    diploma = "diploma"
    masters = "masters"
    btech = "btech"


class Semester(str, enum.Enum):
    s1 = "1"
    s2 = "2"
    annual = "annual"


class VersionStatus(str, enum.Enum):
    draft = "draft"
    review = "review"
    published = "published"
    superseded = "superseded"
    failed = "failed"


class ExtractionMethod(str, enum.Enum):
    geometry = "geometry"
    pdfplumber = "pdfplumber"
    manual = "manual"


class Confidence(str, enum.Enum):
    high = "high"
    low = "low"


class SessionType(str, enum.Enum):
    lecture = "lecture"
    practical = "practical"
    other = "other"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class IssueSeverity(str, enum.Enum):
    info = "info"
    warning = "warning"
    error = "error"


class PublicationAction(str, enum.Enum):
    publish = "publish"
    rollback = "rollback"


class LiveStatus(str, enum.Enum):
    scheduled = "scheduled"
    live = "live"
    ended = "ended"
    not_held = "not_held"


class AdminRole(str, enum.Enum):
    admin = "admin"
    reviewer = "reviewer"
    owner = "owner"
    cr = "cr"  # class representative (operational role, cohort-scoped)


class Institution(UUIDMixin, Base):
    __tablename__ = "institution"
    name: Mapped[str] = mapped_column(Text)
    code: Mapped[str] = mapped_column(String(32), unique=True)


class Programme(UUIDMixin, Base):
    __tablename__ = "programme"
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution.id"))
    name: Mapped[str] = mapped_column(Text)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    level: Mapped[ProgrammeLevel] = mapped_column(_enum(ProgrammeLevel, "programme_level"))
    department: Mapped[str | None] = mapped_column(Text, nullable=True)


class Cohort(UUIDMixin, Base):
    __tablename__ = "cohort"
    programme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programme.id"))
    code: Mapped[str] = mapped_column(String(64), unique=True)
    intake_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    section: Mapped[str | None] = mapped_column(String(16), nullable=True)


class AcademicPeriod(UUIDMixin, Base):
    __tablename__ = "academic_period"
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution.id"))
    year_label: Mapped[str] = mapped_column(String(16))
    semester: Mapped[Semester] = mapped_column(_enum(Semester, "semester"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("institution_id", "year_label", "semester", name="uq_period"),)


class SourceDocument(UUIDMixin, Base):
    __tablename__ = "source_document"
    period_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("academic_period.id"), nullable=True)
    original_filename: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    page_count: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TimetableVersion(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "timetable_version"
    period_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_period.id"))
    source_document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source_document.id"))
    label: Mapped[str] = mapped_column(Text)
    status: Mapped[VersionStatus] = mapped_column(
        _enum(VersionStatus, "version_status"), default=VersionStatus.draft
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sessions: Mapped[list["TimetableSession"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # One active published version per period (partial unique index).
        # `WHERE is_active` is valid on both PostgreSQL and SQLite.
        Index(
            "uq_one_active_version_per_period",
            "period_id",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active"),
        ),
    )


class Course(UUIDMixin, Base):
    __tablename__ = "course"
    name: Mapped[str] = mapped_column(Text)
    code: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    department: Mapped[str | None] = mapped_column(Text, nullable=True)


class Lecturer(UUIDMixin, Base):
    __tablename__ = "lecturer"
    name: Mapped[str] = mapped_column(Text)


class Venue(UUIDMixin, Base):
    __tablename__ = "venue"
    code: Mapped[str] = mapped_column(String(128))
    name: Mapped[str | None] = mapped_column(Text, nullable=True)


class TimetableSession(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "timetable_session"
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timetable_version.id", ondelete="CASCADE"), index=True
    )
    day_of_week: Mapped[int] = mapped_column(SmallInteger)  # Mon=1 .. Fri=5
    start_time: Mapped[datetime.time] = mapped_column(Time)
    end_time: Mapped[datetime.time] = mapped_column(Time)
    course_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("course.id"), nullable=True)
    course_name_raw: Mapped[str] = mapped_column(Text)
    course_code_raw: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    venue_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("venue.id"), nullable=True)
    venue_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    lecturer_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_type: Mapped[SessionType | None] = mapped_column(
        _enum(SessionType, "session_type"), nullable=True
    )
    extraction_method: Mapped[ExtractionMethod] = mapped_column(
        _enum(ExtractionMethod, "extraction_method"), default=ExtractionMethod.geometry
    )
    confidence: Mapped[Confidence] = mapped_column(_enum(Confidence, "confidence"))
    source_page: Mapped[int] = mapped_column(Integer, index=True)
    source_cell_bbox: Mapped[dict | None] = mapped_column(Text, nullable=True)
    source_text_raw: Mapped[str] = mapped_column(Text)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)

    # Operational live status, set in real time by a class representative.
    live_status: Mapped[LiveStatus] = mapped_column(
        _enum(LiveStatus, "live_status"), default=LiveStatus.scheduled
    )
    live_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    live_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Latest operational change (reschedule/swap). Original values are preserved so the
    # student view can show "changed from 08:00 to 10:00" (and from another day).
    rescheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reschedule_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_day_of_week: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    original_start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    original_end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    original_venue_raw: Mapped[str | None] = mapped_column(Text, nullable=True)

    version: Mapped[TimetableVersion] = relationship(back_populates="sessions")


class SessionCohort(Base):
    __tablename__ = "session_cohorts"
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timetable_session.id", ondelete="CASCADE"), primary_key=True
    )
    cohort_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cohort.id"), primary_key=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)


class SessionLecturer(Base):
    __tablename__ = "session_lecturers"
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timetable_session.id", ondelete="CASCADE"), primary_key=True
    )
    lecturer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lecturer.id"), primary_key=True)
    raw_name: Mapped[str] = mapped_column(Text)


class SessionFieldEvidence(UUIDMixin, Base):
    __tablename__ = "session_field_evidence"
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timetable_session.id", ondelete="CASCADE"), index=True
    )
    field_name: Mapped[str] = mapped_column(String(64))
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[Confidence] = mapped_column(_enum(Confidence, "confidence"))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class ImportJob(UUIDMixin, Base):
    __tablename__ = "import_job"
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("timetable_version.id"))
    source_document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source_document.id"))
    status: Mapped[JobStatus] = mapped_column(_enum(JobStatus, "job_status"), default=JobStatus.queued)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    errors: Mapped[dict | None] = mapped_column(Text, nullable=True)
    summary: Mapped[dict | None] = mapped_column(Text, nullable=True)


class ValidationIssue(UUIDMixin, Base):
    __tablename__ = "validation_issue"
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timetable_version.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("timetable_session.id", ondelete="SET NULL"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(64))
    severity: Mapped[IssueSeverity] = mapped_column(_enum(IssueSeverity, "issue_severity"))
    message: Mapped[str] = mapped_column(Text)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PublicationRecord(UUIDMixin, Base):
    __tablename__ = "publication_record"
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("timetable_version.id"))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    action: Mapped[PublicationAction] = mapped_column(_enum(PublicationAction, "publication_action"))
    diff_summary: Mapped[dict | None] = mapped_column(Text, nullable=True)
    previous_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("timetable_version.id"), nullable=True
    )


class AuditEvent(UUIDMixin, Base):
    __tablename__ = "audit_event"
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_user.id"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(64))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(64))
    before: Mapped[dict | None] = mapped_column(Text, nullable=True)
    after: Mapped[dict | None] = mapped_column(Text, nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)


class AdminUser(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "admin_user"
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[AdminRole] = mapped_column(_enum(AdminRole, "admin_role"), default=AdminRole.reviewer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    cohorts: Mapped[list["CohortRepresentative"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class CohortRepresentative(Base):
    """Links a class-representative user (``admin_user`` with role ``cr``) to cohorts."""

    __tablename__ = "cohort_representative"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("admin_user.id", ondelete="CASCADE"), primary_key=True
    )
    cohort_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cohort.id", ondelete="CASCADE"), primary_key=True)

    user: Mapped[AdminUser] = relationship(back_populates="cohorts")


class VenueNotice(UUIDMixin, TimestampMixin, Base):
    """A class rep's heads-up that a venue is (or will soon be) occupied.

    Used so people know when to leave a venue and so a venue is not grabbed by
    mistake. ``active`` notices are those with ``cleared_at IS NULL``.
    """

    __tablename__ = "venue_notice"
    venue: Mapped[str] = mapped_column(String(128), index=True)
    cohort_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cohort.id", ondelete="SET NULL"), nullable=True
    )
    day_of_week: Mapped[int] = mapped_column(SmallInteger)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_user.id", ondelete="SET NULL"), nullable=True
    )
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AdminSession(UUIDMixin, Base):
    __tablename__ = "admin_session"
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("admin_user.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)




















