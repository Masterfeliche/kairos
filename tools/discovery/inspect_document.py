"""Discovery: document-level inspection of the DIT teaching timetable PDF.

Reproduces the facts in docs/00-discovery-report.md (metadata, page count, layout
classification, identifier inventory and placeholder statistics).

Usage:
    python tools/discovery/inspect_document.py [path-to-pdf]
"""
from __future__ import annotations

import re
import sys
import json
from collections import Counter, defaultdict
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
TIME_PAT = re.compile(r"^\d{2}:\d{2}-\d{2}:\d{2}$")
PLACEHOLDERS = {"---", "-x-", "-x"}


def metadata(doc: "fitz.Document") -> dict:
    meta = doc.metadata or {}
    return {k: meta.get(k) for k in (
        "title", "author", "creator", "producer", "creationDate", "modDate"
    )}


def page_ids(doc: "fitz.Document", index: int) -> list[str]:
    found: list[str] = []
    blocks = sorted(doc[index].get_text("blocks"), key=lambda b: (b[1], b[0]))
    for b in blocks[:14]:
        for m in ID_PAT.findall(b[4]):
            if m not in found:
                found.append(m)
    return found


def main() -> None:
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    pdf = pdfplumber.open(str(pdf_path))

    print("=" * 70)
    print("DIT TIMETABLE - DOCUMENT INSPECTION")
    print("=" * 70)
    print(f"file     : {pdf_path.name}")
    print(f"pages    : {len(doc)}")
    print(f"metadata : {json.dumps(metadata(doc), ensure_ascii=False)}")

    dims = Counter()
    for i in range(len(doc)):
        r = doc[i].rect
        dims[(round(r.width), round(r.height), doc[i].rotation)] += 1
    print(f"page size: {dict(dims)}")

    ids_by_page = [page_ids(doc, i) for i in range(len(doc))]
    top_ids = [ids[0] if ids else None for ids in ids_by_page]

    print(f"distinct top-page class ids : {len(set(t for t in top_ids if t))}")
    print(f"pages without class id      : {[i+1 for i,t in enumerate(top_ids) if not t]}")
    multi = [i + 1 for i, ids in enumerate(ids_by_page) if len(ids) > 1]
    print(f"pages referencing >1 cohort : {multi}")

    families: dict[str, list[str]] = defaultdict(list)
    for t in top_ids:
        if not t:
            continue
        m = re.match(r"([A-Z]+\d{2}|MASTERS)", t)
        if m:
            families[m.group(0)].append(t)
    print("class-id families:")
    for fam in sorted(families):
        uniq = sorted(set(families[fam]))
        print(f"  {fam:<10} {len(uniq):>3}  {', '.join(uniq)}")

    placeholders = Counter()
    tables_per_page = Counter()
    sessions = 0
    total_cells = 0
    no_code = 0
    for i in range(len(pdf.pages)):
        tables = pdf.pages[i].extract_tables()
        tables_per_page[len(tables)] += 1
        if not tables:
            continue
        for row in tables[0]:
            if not row or not row[0] or not TIME_PAT.match(str(row[0]).strip()):
                continue
            for cell in row[1:]:
                total_cells += 1
                if cell is None:
                    continue
                s = cell.strip()
                if s in PLACEHOLDERS:
                    placeholders[s] += 1
                    continue
                sessions += 1
                if "(" not in s.replace("\n", " "):
                    no_code += 1

    print(f"tables per page       : {dict(tables_per_page)}")
    print(f"grid cells (Mon-Fri)  : {total_cells}")
    print(f"teaching sessions     : {sessions}")
    print(f"placeholders          : {dict(placeholders)}")

    doc.close()
    pdf.close()


if __name__ == "__main__":
    main()
