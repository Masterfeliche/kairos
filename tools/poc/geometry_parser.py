"""Phase 1 PoC: geometry-first timetable parser.

Why geometry-first? Discovery showed that off-the-shelf table extractors
(pdfplumber, PyMuPDF find_tables) drop or misroute wrapped course codes such as
"(CSEU" + "07102)" on page 42. This parser reconstructs the grid from the page's
vector rules and assigns words by coordinate, so wrapped tokens are rejoined.

It is intentionally a prototype: heuristics are explicit, every uncertain value is
flagged, and nothing is fabricated.

Usage:
    python tools/poc/geometry_parser.py [path-to-pdf] [out.json]
"""
from __future__ import annotations

import re
import sys
import json
import bisect
from pathlib import Path
from collections import defaultdict

import pymupdf as fitz

DEFAULT_PDF = Path(__file__).resolve().parents[2] / (
    "TEACHING TIMETABLE 2026-2025 - SEMESTER I - Students.pdf"
)

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
TIME_PAT = re.compile(r"^(\d{2}):(\d{2})-(\d{2}):(\d{2})$")
CODE_PAT = re.compile(r"\(([A-Z]{2,4})\s?([A-Z]?\d{3,5})\s?\)")
ID_PAT = re.compile(
    r"(BENG\d{2}[A-Z]+-\d+|BT\d{2}[A-Z]+-\d+|OD\d{2}[A-Z]+-\d+|"
    r"MC\d{2}[A-Z]+|MT\d{2}[A-Z]+|MT[A-Z]+\d+-\d+|MASTERS-[A-Z]+)",
    re.I,
)
PLACEHOLDERS = {"---", "-x-", "-x"}

# department / stream tokens that may follow a course code
DEPT_TOKENS = {
    "CS", "CIVIL", "GS", "EE", "LS", "MECH", "ETE", "ELECTRICAL",
    "CIVIL_GEO", "MASTERS-CS", "MASTERS-SE", "MASTERS-MM", "MASTERS-ETE",
}
PRACTICAL_RE = re.compile(r"(\([PL]\)|-P\b|-L\b)", re.I)


def cluster(values: list[float], tol: float = 1.8) -> list[float]:
    """Merge near-duplicate rule coordinates (double lines from Excel export)."""
    values = sorted(values)
    out: list[float] = []
    for v in values:
        if not out or v - out[-1] > tol:
            out.append(v)
        else:
            out[-1] = (out[-1] + v) / 2
    return out


def page_rules(page: "fitz.Page") -> tuple[list[float], list[tuple[float, float, float]]]:
    """Return (vertical x's, horizontal segments as (y, x0, x1)).

    Horizontal segments are kept per-segment (not merged across the page) because
    merged multi-hour cells give different row boundaries in different day columns.
    """
    width, height = page.rect.width, page.rect.height
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


def repr_rules(page: "fitz.Page") -> tuple[list[float], list[tuple[float, float, float]]]:
    """Fallback when a page has no usable ruling lines: derive from word geometry."""
    xs: list[float] = []
    ys: list[float] = []
    for w in page.get_text("words"):
        xs.extend([w[0], w[2]])
        ys.extend([w[1], w[3]])
    xs = cluster(xs)
    y_cluster = cluster(ys)
    width = page.rect.width
    hsegs = [(y, 0.0, width) for y in y_cluster]
    return xs, hsegs


def top_cohort(page: "fitz.Page") -> list[str]:
    found: list[str] = []
    for b in sorted(page.get_text("blocks"), key=lambda b: (b[1], b[0]))[:14]:
        for m in ID_PAT.findall(b[4]):
            if m not in found:
                found.append(m)
    return found


def parse_cell(joined: str) -> dict:
    """Split a cell's text into course/lecturer/venue + flags. Uncertain ⇒ flagged."""
    reasons: list[str] = []
    codes = CODE_PAT.findall(joined)
    course_code = f"{codes[0][0]} {codes[0][1]}" if codes else None
    if not codes:
        reasons.append("MISSING_CODE")

    # best-effort: text after the last code is "dept + lecturer + venue"
    tail = joined
    if codes:
        last = list(CODE_PAT.finditer(joined))[-1]
        tail = joined[last.end():].strip()
    tokens = [t for t in re.split(r"\s{1,}", tail) if t]

    department = None
    if tokens:
        first = tokens[0].strip(".,()")
        if first.upper() in {d.upper() for d in DEPT_TOKENS}:
            department = first
            tokens = tokens[1:]

    session_type = "practical" if PRACTICAL_RE.search(joined) else "lecture"
    return {
        "course_code": course_code,
        "department": department,
        "tail": " ".join(tokens),
        "session_type": session_type,
        "reasons": reasons,
    }


def main() -> None:
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("poc_sessions.json")

    doc = fitz.open(pdf_path)
    sessions: list[dict] = []
    continuation_cohort: str | None = None
    cells_repaired: list[dict] = []

    for pno in range(len(doc)):
        page = doc[pno]
        words = page.get_text("words")  # (x0,y0,x1,y1,text,block,line,word_no)
        vx, hsegs = page_rules(page)
        if len(vx) < 3 or len(hsegs) < 3:  # degenerate page
            vx, hsegs = repr_rules(page)

        # The "Timetable generated on ..." footer sits below the grid; drop it and
        # anything beneath it so it never becomes a phantom session.
        footer_y = None
        for b in page.get_text("blocks"):
            if "Timetable generated" in b[4]:
                footer_y = b[1]
                break
        if footer_y is not None:
            words = [w for w in words if w[1] < footer_y - 1]

        # day columns = gaps between vertical rules; drop the first (time) column
        cols = [(vx[i], vx[i + 1]) for i in range(len(vx) - 1)]
        if len(cols) < 5:
            continue
        day_cols = cols[-5:] if len(cols) >= 5 else cols

        # time-slot labels -> (start_minutes, y)
        slots: list[tuple[int, float]] = []
        for w in words:
            m = TIME_PAT.match(w[4])
            if m:
                start = int(m.group(1)) * 60 + int(m.group(2))
                slots.append((start, w[1]))
        slots.sort(key=lambda s: s[1])

        codes_on_page = top_cohort(page)
        if codes_on_page:
            continuation_cohort = codes_on_page[0]
        cohort = continuation_cohort

        # Per-column row bands: only horizontal segments that actually span the
        # column bound its cells. This keeps merged multi-hour sessions intact.
        col_bands: dict[int, list[tuple[float, float]]] = {}
        for ci, (cx0, cx1) in enumerate(day_cols):
            ys = cluster([y for (y, x0, x1) in hsegs
                          if x0 <= cx0 + 2 and x1 >= cx1 - 2])
            col_bands[ci] = [(ys[j], ys[j + 1]) for j in range(len(ys) - 1)]

        buckets: dict[tuple, list[tuple[float, float, str]]] = defaultdict(list)
        for w in words:
            x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
            if TIME_PAT.match(text):
                continue  # time labels live in the left column
            cx = (x0 + x1) / 2
            cy = (y0 + y1) / 2
            col_idx = None
            for ci, (a, b) in enumerate(day_cols):
                if a <= cx <= b:
                    col_idx = ci
                    break
            if col_idx is None:
                continue
            band_idx = None
            for bi, (a, b) in enumerate(col_bands[col_idx]):
                if a <= cy <= b:
                    band_idx = bi
                    break
            if band_idx is None:
                continue
            buckets[(col_idx, band_idx)].append((y0, x0, text))

        # --- cell text assembly -------------------------------------------------
        cell_text: dict[tuple[int, int], str] = {}
        for key, toks in buckets.items():
            toks.sort()
            cell_text[key] = re.sub(r"\s+", " ", " ".join(t[2] for t in toks)).strip()

        # --- repair pass: Excel text-overflow spilling a wrapped code's digits
        # into the adjacent (right) cell, e.g. "(CSEU" | "07102)" on the same row.
        open_code = re.compile(r"\(([A-Z]{2,4})\s*$")
        close_code = re.compile(r"^(\d{3,5})\s?\)")
        for (col_idx, band_idx), text in list(cell_text.items()):
            m = open_code.search(text)
            if not m:
                continue
            right = cell_text.get((col_idx + 1, band_idx))
            if not right:
                continue
            n = close_code.match(right)
            if not n:
                continue
            cell_text[(col_idx, band_idx)] = f"{text}{n.group(1)}) {close_code.sub('', right).strip()}".strip()
            cell_text[(col_idx + 1, band_idx)] = close_code.sub("", right).strip()
            cells_repaired.append({"page": pno + 1, "code": f"{m.group(1)} {n.group(1)}"})

        for (col_idx, band_idx), joined0 in sorted(cell_text.items()):
            joined = joined0
            if not joined or joined in PLACEHOLDERS:
                continue
            if joined.startswith("Timetable generated"):
                continue
            if re.fullmatch(r"\d{1,2}:\d{2}\s?(AM|PM)", joined, re.I):
                continue  # footer remnant
            if joined in DAYS:
                continue  # header row
            if "DAR ES SALAAM" in joined.upper() or "INSTITUTE OF TECHNOLOGY" in joined.upper():
                continue
            if ID_PAT.fullmatch(joined.strip()):
                continue  # class-id header line
            parsed = parse_cell(joined)

            band_top, band_bottom = col_bands[col_idx][band_idx]
            labels_in_band = [s for s in slots if band_top - 2 <= s[1] <= band_bottom + 2]
            if labels_in_band:
                # The session runs from the first to the last hour label that its
                # cell spans. More than one label ⇒ a genuine multi-hour session.
                start_min = min(s[0] for s in labels_in_band)
                end_min = max(s[0] for s in labels_in_band) + 60
            else:
                above = [s for s in slots if s[1] <= band_top]
                if not above:
                    continue
                start_min = above[-1][0]
                end_min = start_min + 60
            multi_row = len(labels_in_band) > 1

            others = [x for x in ID_PAT.findall(joined) if x != cohort]
            reasons = list(parsed["reasons"])
            confidence = "low" if reasons else "high"
            sessions.append({
                "page": pno + 1,
                "cohort": cohort,
                "day": DAYS[col_idx] if col_idx < len(DAYS) else None,
                "start_time": f"{start_min // 60:02d}:{start_min % 60:02d}",
                "end_time": f"{end_min // 60:02d}:{end_min % 60:02d}",
                "course_code": parsed["course_code"],
                "department": parsed["department"],
                "cell_text": joined,
                "shared_with": others,
                "session_type": parsed["session_type"],
                "extraction_method": "geometry",
                "confidence": confidence,
                "reasons": reasons,
                "multi_row_band": multi_row,
            })

    report = {
        "pages": len(doc),
        "sessions": len(sessions),
        "with_code": sum(1 for s in sessions if s["course_code"]),
        "without_code": sum(1 for s in sessions if not s["course_code"]),
        "shared": sum(1 for s in sessions if s["shared_with"]),
        "low_confidence": sum(1 for s in sessions if s["confidence"] == "low"),
        "overflow_cells_repaired": len(cells_repaired),
    }
    out_path.write_text(
        json.dumps({"report": report, "sessions": sessions,
                    "repaired": cells_repaired}, indent=1, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    print(f"wrote {out_path}")
    doc.close()


if __name__ == "__main__":
    main()
