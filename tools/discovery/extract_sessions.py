"""Discovery: naive session extraction + geometry evidence.

Produces a baseline extraction (course code, cohort, day, slot, raw cell) and reports
the difficult cases described in docs/00-discovery-report.md:
  - course-code wrap spill
  - shared / combined cohorts
  - multi-hour sessions (adjacent repeated cells)

This is deliberately NOT the production parser. It exists to prove feasibility and to
seed the PoC gold set.

Usage:
    python tools/discovery/extract_sessions.py [path-to-pdf] [out.json]
"""
from __future__ import annotations

import re
import sys
import json
from collections import Counter
from pathlib import Path

import pymupdf as fitz
import pdfplumber

DEFAULT_PDF = Path(__file__).resolve().parents[2] / (
    "TEACHING TIMETABLE 2026-2025 - SEMESTER I - Students.pdf"
)

ID_PAT = re.compile(
    r"(BENG\d{2}[A-Z]+-\d+|BT\d{2}[A-Z]+-\d+|OD\d{2}[A-Z]+-\d+|"
    r"MC\d{2}[A-Z]+|MT\d{2}[A-Z]+|MT[A-Z]+\d+-\d+|MASTERS-[A-Z]+)",
    re.I,
)
CODE_PAT = re.compile(r"\(([A-Z]{2,4})\s?(\d{3,5})\s?\)")
TIME_PAT = re.compile(r"^\d{2}:\d{2}-\d{2}:\d{2}$")
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
PLACEHOLDERS = {"---", "-x-", "-x"}


def top_ids(doc: "fitz.Document", index: int) -> list[str]:
    found: list[str] = []
    for b in sorted(doc[index].get_text("blocks"), key=lambda b: (b[1], b[0]))[:14]:
        for m in ID_PAT.findall(b[4]):
            if m not in found:
                found.append(m)
    return found


def main() -> None:
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("sessions.json")

    doc = fitz.open(pdf_path)
    pdf = pdfplumber.open(str(pdf_path))

    sessions: list[dict] = []
    no_code: list[dict] = []
    shared: list[dict] = []
    adjacent_repeats = 0
    class_id: str | None = None

    for i in range(len(pdf.pages)):
        ids = top_ids(doc, i)
        if ids:
            class_id = ids[0]  # carry forward for continuation pages (e.g. p.75)
        tables = pdf.pages[i].extract_tables()
        if not tables:
            continue
        rows = [r for r in tables[0] if r and r[0] and TIME_PAT.match(str(r[0]).strip())]
        for col in range(1, 6):
            prev_code = None
            for row in rows:
                if col >= len(row) or not row[col]:
                    prev_code = None
                    continue
                cell = row[col].strip()
                if cell in PLACEHOLDERS:
                    prev_code = None
                    continue
                joined = re.sub(r"\s+", " ", cell.replace("\n", " ")).strip()
                codes = CODE_PAT.findall(joined)
                if not codes:
                    no_code.append({"page": i + 1, "day": DAYS[col - 1],
                                    "slot": str(row[0]).strip(), "cell": joined})
                    prev_code = None
                    continue
                code = f"{codes[0][0]} {codes[0][1]}"
                others = [x for x in ID_PAT.findall(joined) if x != class_id]
                if others:
                    shared.append({"page": i + 1, "cohort": class_id,
                                   "also": others, "cell": joined[:90]})
                if code == prev_code:
                    adjacent_repeats += 1
                prev_code = code
                sessions.append({
                    "page": i + 1, "cohort": class_id, "day": DAYS[col - 1],
                    "slot": str(row[0]).strip(), "code": code, "cell": joined,
                    "confidence": "high",
                })

    report = {
        "pages": len(doc),
        "sessions": len(sessions),
        "cells_without_code": len(no_code),
        "shared_cohort_cells": len(shared),
        "adjacent_same_code_cells": adjacent_repeats,
        "placeholder_counts": Counter(),
    }
    out_path.write_text(
        json.dumps({"report": report, "sessions": sessions,
                    "no_code": no_code, "shared": shared}, indent=1, ensure_ascii=False),
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nwrote {out_path}")

    doc.close()
    pdf.close()


if __name__ == "__main__":
    main()
