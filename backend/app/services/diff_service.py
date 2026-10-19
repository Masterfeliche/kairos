"""Version diffing by stable session identity (docs/04-data-model.md §5.3)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.extraction.normalise import session_identity_key
from app.models import Cohort, SessionCohort, TimetableSession, TimetableVersion

COMPARE_FIELDS = [
    "day_of_week",
    "start_time",
    "end_time",
    "course_code_raw",
    "course_name_raw",
    "lecturer_raw",
    "venue_raw",
    "session_type",
    "cohort_codes",
]


def _coded(value) -> str:
    return "" if value is None else str(value)


def load_sessions(session: Session, version_id) -> dict[str, dict]:
    rows = session.execute(
        select(TimetableSession).where(TimetableSession.version_id == version_id)
    ).scalars().all()

    cohort_map: dict = {}
    links = session.execute(
        select(SessionCohort.session_id, Cohort.code)
        .join(Cohort, Cohort.id == SessionCohort.cohort_id)
    ).all()
    for sid, code in links:
        cohort_map.setdefault(sid, []).append(code)

    out: dict[str, dict] = {}
    for s in rows:
        record = {
            "id": str(s.id),
            "day_of_week": s.day_of_week,
            "start_time": _coded(s.start_time),
            "end_time": _coded(s.end_time),
            "course_code_raw": s.course_code_raw,
            "course_name_raw": s.course_name_raw,
            "lecturer_raw": s.lecturer_raw,
            "venue_raw": s.venue_raw,
            "session_type": s.session_type.value if s.session_type else None,
            "cohort_codes": sorted(cohort_map.get(s.id, [])),
            "source_page": s.source_page,
        }
        key = session_identity_key({**record, "cohort_codes": record["cohort_codes"]})
        out[key] = record
    return out


def active_version_id(session: Session, period_id) -> object | None:
    v = session.execute(
        select(TimetableVersion).where(
            TimetableVersion.period_id == period_id,
            TimetableVersion.is_active.is_(True),
        )
    ).scalar_one_or_none()
    return v.id if v else None


def diff_versions(session: Session, version_id, base_version_id=None) -> dict:
    target = session.get(TimetableVersion, version_id)
    if target is None:
        raise ValueError("version not found")

    if base_version_id is None:
        base_version_id = active_version_id(session, target.period_id)

    target_sessions = load_sessions(session, version_id)
    base_sessions = load_sessions(session, base_version_id) if base_version_id else {}

    added, removed, changed = [], [], []
    for key, rec in target_sessions.items():
        if key not in base_sessions:
            added.append({k: rec[k] for k in ("day_of_week", "start_time", "course_code_raw",
                                              "course_name_raw", "cohort_codes", "source_page")})
        else:
            base = base_sessions[key]
            fields = {
                f: {"from": base[f], "to": rec[f]}
                for f in COMPARE_FIELDS if base[f] != rec[f]
            }
            if fields:
                changed.append({
                    "key": key,
                    "session_id": rec["id"],
                    "source_page": rec["source_page"],
                    "cohort_codes": rec["cohort_codes"],
                    "course_code_raw": rec["course_code_raw"],
                    "fields": fields,
                })
    for key, rec in base_sessions.items():
        if key not in target_sessions:
            removed.append({k: rec[k] for k in ("day_of_week", "start_time", "course_code_raw",
                                                "course_name_raw", "cohort_codes", "source_page")})

    return {
        "version_id": str(version_id),
        "base_version_id": str(base_version_id) if base_version_id else None,
        "added": added,
        "removed": removed,
        "changed": changed,
        "summary": {"added": len(added), "removed": len(removed), "changed": len(changed)},
    }
