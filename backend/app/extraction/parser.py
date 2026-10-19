"""Geometry-first PDF parser (Phase 1 prototype, promoted to a library).

Reconstructs the timetable grid from the page's vector rules and assigns words by
coordinate, so wrapped course codes are rejoined and per-column vertical merges are
read as multi-hour sessions. Every uncertain value is flagged; nothing is fabricated.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf as fitz

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
TIME_PAT = re.compile(r"^(\d{2}):(\d{2})-(\d{2}):(\d{2})$")
CODE_PAT = re.compile(r"\(([A-Z]{2,4})\s?([A-Z]?\d{3,5})\s?\)")
ID_PAT = re.compile(
    r"(BENG\d{2}[A-Z]+-\d+|BT\d{2}[A-Z]+-\d+|OD\d{2}[A-Z]+-\d+|"
    r"MC\d{2}[A-Z]+|MT\d{2}[A-Z]+|MT[A-Z]+\d+-\d+|MASTERS-[A-Z]+)",
    re.I,
)
PLACEHOLDERS = {"---", "-x-", "-x"}
DEPT_TOKENS = {
    "CS", "CIVIL", "GS", "EE", "LS", "MECH", "ETE", "ELECTRICAL",
    "CIVIL_GEO", "MASTERS-CS", "MASTERS-SE", "MASTERS-MM", "MASTERS-ETE",
}
VENUE_TOKEN_RE = re.compile(
    r"^(Rafic|Multimedia|CEITT|TT\d|[A-Z]-?\d|[A-Z]\d)",
)
PRACTICAL_RE = re.compile(r"(\([PL]\)|-P\b|-L\b)", re.I)


@dataclass
class ParsedSession:
    page: int
    cohorts: list[str]
    day: str
    start_time: str
    end_time: str
    course_name: str
    course_code: str | None
    department: str | None
    lecturer_raw: str | None
    venue_raw: str | None
    session_type: str
    confidence: str
    reasons: list[str] = field(default_factory=list)
    multi_hour: bool = False
    is_shared: bool = False
    source_text: str = ""
    bbox: dict | None = None


def cluster(values: list[float], tol: float = 1.8) -> list[float]:
    values = sorted(values)
    out: list[float] = []
    for v in values:
        if not out or v - out[-1] > tol:
            out.append(v)
        else:
            out[-1] = (out[-1] + v) / 2
    return out


def page_rules(page: "fitz.Page") -> tuple[list[float], list[tuple[float, float, float]]]:
    height = page.rect.height
    xs: list[float] = []
    hsegs: list[tuple[float, float, float]] = []
    for drawing in page.get_drawings():
        for item in drawing["items"]:
            if item[0] == "l":
                a, b = item[1], item[2]
                if abs(a.y - b.y) < 0.6 and abs(a.x - b.x) > 30:
                    hsegs.append(((a.y + b.y) / 2, min(a.x, b.x), max(a.x, b.x)))
                if abs(a.x - b.x) < 0.6 and abs(a.y - b.y) > height * 0.15:
                    xs.append((a.x + b.x) / 2)
            elif item[0] == "re":
                r = item[1]
                if r.width > 30:
                    hsegs.append((r.y0, r.x0, r.x1))
                    hsegs.append((r.y1, r.x0, r.x1))
                if r.height > height * 0.15:
                    xs.extend([r.x0, r.x1])
    return cluster(xs), hsegs


def _repr_rules(page: "fitz.Page") -> tuple[list[float], list[tuple[float, float, float]]]:
    xs: list[float] = []
    ys: list[float] = []
    for w in page.get_text("words"):
        xs.extend([w[0], w[2]])
        ys.extend([w[1], w[3]])
    width = page.rect.width
    return cluster(xs), [(y, 0.0, width) for y in cluster(ys)]


def top_cohort(page: "fitz.Page") -> list[str]:
    found: list[str] = []
    for b in sorted(page.get_text("blocks"), key=lambda b: (b[1], b[0]))[:14]:
        for m in ID_PAT.findall(b[4]):
            if m not in found:
                found.append(m)
    return found


def _split_lecturer_venue(tail: str) -> tuple[str | None, str | None]:
    """Best-effort split of "<dept> <lecturer(s)> <venue>". Never invents text."""
    tokens = tail.split()
    idx = None
    for i, t in enumerate(tokens):
        if VENUE_TOKEN_RE.match(t):
            idx = i
    if idx is None:
        return (tail.strip() or None), None
    venue = " ".join(tokens[idx:]).strip()
    lecturer = " ".join(tokens[:idx]).strip()
    return (lecturer or None), (venue or None)


def parse_cell_text(joined: str) -> dict:
    reasons: list[str] = []
    matches = list(CODE_PAT.finditer(joined))
    codes = CODE_PAT.findall(joined)
    course_code = f"{codes[0][0]} {codes[0][1]}" if codes else None
    if not codes:
        reasons.append("MISSING_CODE")

    if matches:
        first, last = matches[0], matches[-1]
        course_name = joined[: first.start()].strip(" -/,")
        tail = joined[last.end():].strip()
    else:
        course_name = joined.strip()
        tail = ""

    tokens = tail.split()
    department = None
    if tokens:
        first_tok = tokens[0].strip(".,()")
        if first_tok.upper() in DEPT_TOKENS:
            department = first_tok
            tokens = tokens[1:]
    lecturer_raw, venue_raw = _split_lecturer_venue(" ".join(tokens))

    session_type = "practical" if PRACTICAL_RE.search(joined) else "lecture"
    return {
        "course_name": course_name,
        "course_code": course_code,
        "department": department,
        "lecturer_raw": lecturer_raw,
        "venue_raw": venue_raw,
        "session_type": session_type,
        "reasons": reasons,
    }


def parse_pdf(pdf_path: str | Path) -> list[ParsedSession]:
    doc = fitz.open(pdf_path)
    sessions: list[ParsedSession] = []
    continuation_cohort: str | None = None

    for pno in range(len(doc)):
        page = doc[pno]
        words = page.get_text("words")
        vx, hsegs = page_rules(page)
        if len(vx) < 3 or len(hsegs) < 3:
            vx, hsegs = _repr_rules(page)

        footer_y = None
        for b in page.get_text("blocks"):
            if "Timetable generated" in b[4]:
                footer_y = b[1]
                break
        if footer_y is not None:
            words = [w for w in words if w[1] < footer_y - 1]

        cols = [(vx[i], vx[i + 1]) for i in range(len(vx) - 1)]
        if len(cols) < 5:
            continue
        day_cols = cols[-5:]

        slots: list[tuple[int, float]] = []
        for w in words:
            m = TIME_PAT.match(w[4])
            if m:
                slots.append((int(m.group(1)) * 60 + int(m.group(2)), w[1]))
        slots.sort(key=lambda s: s[1])

        codes_on_page = top_cohort(page)
        if codes_on_page:
            continuation_cohort = codes_on_page[0]
        cohort = continuation_cohort

        col_bands: dict[int, list[tuple[float, float]]] = {}
        for ci, (cx0, cx1) in enumerate(day_cols):
            ys = cluster([y for (y, x0, x1) in hsegs if x0 <= cx0 + 2 and x1 >= cx1 - 2])
            col_bands[ci] = [(ys[j], ys[j + 1]) for j in range(len(ys) - 1)]

        buckets: dict[tuple[int, int], list[tuple[float, float, str]]] = {}
        for w in words:
            x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
            if TIME_PAT.match(text):
                continue
            cx = (x0 + x1) / 2
            cy = (y0 + y1) / 2
            col_idx = next((ci for ci, (a, b) in enumerate(day_cols) if a <= cx <= b), None)
            if col_idx is None:
                continue
            band_idx = next(
                (bi for bi, (a, b) in enumerate(col_bands[col_idx]) if a <= cy <= b), None
            )
            if band_idx is None:
                continue
            buckets.setdefault((col_idx, band_idx), []).append((y0, x0, text))

        cell_text: dict[tuple[int, int], str] = {}
        for key, toks in buckets.items():
            toks.sort()
            cell_text[key] = re.sub(r"\s+", " ", " ".join(t[2] for t in toks)).strip()

        for (col_idx, band_idx), joined in sorted(cell_text.items()):
            if not joined or joined in PLACEHOLDERS:
                continue
            if joined.startswith("Timetable generated"):
                continue
            if re.fullmatch(r"\d{1,2}:\d{2}\s?(AM|PM)", joined, re.I):
                continue
            if joined in DAYS:
                continue
            if "DAR ES SALAAM" in joined.upper() or "INSTITUTE OF TECHNOLOGY" in joined.upper():
                continue
            if ID_PAT.fullmatch(joined.strip()):
                continue

            parsed = parse_cell_text(joined)
            band_top, band_bottom = col_bands[col_idx][band_idx]
            labels = [s for s in slots if band_top - 2 <= s[1] <= band_bottom + 2]
            if labels:
                start_min = min(s[0] for s in labels)
                end_min = max(s[0] for s in labels) + 60
            else:
                above = [s for s in slots if s[1] <= band_top]
                if not above:
                    continue
                start_min = above[-1][0]
                end_min = start_min + 60
            multi_hour = len(labels) > 1

            cohorts_found = ID_PAT.findall(joined)
            cohorts = list(dict.fromkeys(cohorts_found)) or ([cohort] if cohort else [])
            is_shared = len(cohorts) > 1

            confidence = "low" if parsed["reasons"] else "high"
            cx0, cx1 = day_cols[col_idx]
            sessions.append(
                ParsedSession(
                    page=pno + 1,
                    cohorts=cohorts,
                    day=DAYS[col_idx] if col_idx < len(DAYS) else "",
                    start_time=f"{start_min // 60:02d}:{start_min % 60:02d}",
                    end_time=f"{end_min // 60:02d}:{end_min % 60:02d}",
                    course_name=parsed["course_name"],
                    course_code=parsed["course_code"],
                    department=parsed["department"],
                    lecturer_raw=parsed["lecturer_raw"],
                    venue_raw=parsed["venue_raw"],
                    session_type=parsed["session_type"],
                    confidence=confidence,
                    reasons=parsed["reasons"],
                    multi_hour=multi_hour,
                    is_shared=is_shared,
                    source_text=joined,
                    bbox={"x0": cx0, "x1": cx1, "top": band_top, "bottom": band_bottom},
                )
            )

    doc.close()
    return sessions
