"""Service layer re-exports."""
from app.services.audit_service import record as audit_record
from app.services.auth_service import (
    AuthError,
    authenticate,
    create_admin,
    issue_session,
    resolve_session,
    revoke_session,
)
from app.services.correction_service import (
    CorrectionError,
    apply_correction,
    resolve_issue,
)
from app.services.cr_service import (
    CrError,
    clear_venue_notice,
    create_cr,
    create_venue_notice,
    cr_cohorts,
    institute_sessions,
    list_venue_notices,
    reschedule_session,
    room_availability,
    set_live_status,
    swap_sessions,
)
from app.services.diff_service import diff_versions, load_sessions
from app.services.import_service import ImportSummary, import_pdf, infer_programme
from app.services.publish_service import PublishError, publish, rollback
from app.services.rendering import render_pages
from app.services.session_view import collect_details, session_to_dict
from app.services.version_service import resolve_live_version

__all__ = [
    "ImportSummary",
    "import_pdf",
    "infer_programme",
    "publish",
    "rollback",
    "PublishError",
    "render_pages",
    "AuthError",
    "authenticate",
    "create_admin",
    "issue_session",
    "resolve_session",
    "revoke_session",
    "audit_record",
    "CorrectionError",
    "apply_correction",
    "resolve_issue",
    "diff_versions",
    "load_sessions",
    "CrError",
    "create_cr",
    "cr_cohorts",
    "set_live_status",
    "reschedule_session",
    "swap_sessions",
    "institute_sessions",
    "room_availability",
    "create_venue_notice",
    "list_venue_notices",
    "clear_venue_notice",
    "collect_details",
    "session_to_dict",
    "resolve_live_version",
]
