"""Normalisation: ParsedSession -> canonical, storage-ready values.

Normalisation rules (see docs/04-data-model.md §5.3): uppercase, collapse whitespace,
canonical code spacing, canonical time. Nothing is guessed.
"""
from __future__ import annotations

import hashlib
import re
from datetime import time

from app.extraction.parser import DAYS, ParsedSession

_WS = re.compile(r"\s+")


def norm_text(value: str | None) -> str | None:
    if value is None:
        return None
    return _WS.sub(" ", value).strip()


def norm_code(value: str | None) -> str | None:
    if not value:
        return None
    return _WS.sub(" ", value).strip().upper()


def day_index(day: str) -> int | None:
    return DAYS.index(day) + 1 if day in DAYS else None


def to_time(hhmm: str) -> time | None:
    m = re.match(r"^(\d{2}):(\d{2})$", hhmm or "")
    if not m:
        return None
    return time(int(m.group(1)), int(m.group(2)))


def session_identity_key(normalised: dict) -> str:
    """Stable key for version diffs (docs/04-data-model.md §5.3)."""
    parts = [
        str(normalised["day_of_week"]),
        str(normalised["start_time"]),
        str(normalised["end_time"]),
        norm_code(normalised.get("course_code_raw") or normalised.get("course_name_raw")) or "",
        ",".join(sorted(normalised.get("cohort_codes") or [])),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def normalise(parsed: ParsedSession) -> dict:
    lecturer = norm_text(parsed.lecturer_raw)
    return {
        "day_of_week": day_index(parsed.day),
        "start_time": to_time(parsed.start_time),
        "end_time": to_time(parsed.end_time),
        "course_name_raw": norm_text(parsed.course_name) or "",
        "course_code_raw": norm_code(parsed.course_code),
        "department": norm_text(parsed.department),
        "lecturer_raw": lecturer,
        "venue_raw": norm_text(parsed.venue_raw),
        "session_type": parsed.session_type,
        "confidence": parsed.confidence,
        "source_page": parsed.page,
        "source_text_raw": parsed.source_text,
        "source_cell_bbox": parsed.bbox,
        "is_shared": parsed.is_shared,
        "multi_hour": parsed.multi_hour,
        "cohort_codes": [c.upper() for c in parsed.cohorts],
        "reasons": list(parsed.reasons),
    }


def lecturer_parts(lecturer_raw: str | None) -> list[str]:
    """Split a raw lecturer string into individual names (best effort)."""
    if not lecturer_raw:
        return []
    parts = re.split(r",|/|&|\band\b", lecturer_raw, flags=re.I)
    return [p.strip(" .") for p in parts if p.strip(" .")]
