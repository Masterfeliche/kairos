# 4. Extraction Proof-of-Concept Plan

Goal: prove we can turn the actual PDF into reliable, traceable structured sessions **before**
committing to the production architecture. Discovery already established the PDF has a clean text
layer and regular grid geometry (artifact 1), so the PoC is about *accuracy and edge cases*, not OCR.

## 4.1 Representative page set (stratified from the real document)

| Sample | Page | Why |
|---|---|---|
| A | 1 `BENG23BEBE-1` | Dense single-cohort grid with wrapped codes |
| B | 2 `BENG23CE-1` | Standard department grid |
| C | 3 `BENG23CE-2` | All `-x-` blocked sheet (empty state) |
| D | 42 `BENG25COE-*` | Wrapped code spill (`(CSEU` / `07102)`) + merged rows |
| E | 74–75 `BT23LS-1` | Continuation page (no header on p.75) |
| F | 93 `MTCC26-1` | Electives + shared cohorts (`MASTERS-CS`) |
| G | 134/147/152 `OD26*` | Shared cohorts (`OD26ETE-1, OD26AUTO-1`) |
| H | 160 | Multi-table page (L4) |
| I | 126 `OD25FST-1`, 129 `OD25ME-1` | Very dense cells, multiple lecturers |

## 4.2 Candidate tooling (evaluated against this document)

| Tool | Role | Finding from discovery |
|---|---|---|
| **PyMuPDF (fitz)** | words + coordinates + vector rules (`get_drawings`) | Best for geometry reconstruction; rules detected cleanly (x≈51/108/210/323/460/598/735) |
| **pdfplumber** | tables/cells, chars | Good structure but code spill + merged-row misalignment |
| **pdfminer.six** | underlying char stream (via pdfplumber) | Useful for char-level repair |
| **OCR (Tesseract/PaddleOCR)** | fallback for image-only pages | **Not required** — text layer present |

**Recommendation:** geometry-first parser (PyMuPDF words + rules) as primary; pdfplumber tables as
cross-check/fallback. OCR kept only as a dormant adapter.

## 4.3 Proposed extraction algorithm

```
1. Open PDF; validate it is not encrypted/JS; page count sanity.
2. Per page:
   a. Locate header row (Monday..Friday) and the class/cohort id (top-centre).
      - If absent: treat as continuation of previous page (carry cohort).
   b. Detect vertical rules -> day-column x-ranges; detect horizontal rules -> time-row y-ranges.
   c. Collect words (x0,y0,x1,y1,text) and assign each word to a cell by centre point.
   d. Reassemble cell text line-by-line (sort by y then x); this recovers wrapped codes like
      "(CSEU" + "07102)" that table extractors drop.
   e. Classify placeholder cells (--- , -x-).
3. Parse a non-empty cell into a logical session:
   a. Extract course code  : r"\((?P<code>[A-Z]{2,4})\s?(?P<num>\d{3,5})\s?\)"
   b. Extract department    : token(s) after the code, whitelist + fallback.
   c. Extract flags         : -P/-L, (P)/(L) = practical/lecture.
   d. Extract shared cohorts: any class-id token(s) in the cell != page cohort.
   e. Remaining trailing token(s) = venue; preceding name-like line(s) = lecturer(s).
   f. Everything uncertain is recorded as a field with confidence=low + a reason.
4. Merge merged-row cells into a single session with start/end spanning the slot range.
5. Emit records with full provenance: page, cell bbox, raw text, method, confidence.
```

## 4.4 One logical session from multiple cells

- **Multi-hour**: detect a cell whose row rect spans >1 hourly slot (taller row / merged grid
  region) → one session with `start_time` = top slot, `end_time` = bottom slot. Do **not** duplicate.
- **Adjacent repeated cells** (13 found): merge only when course code, cohort, day and contiguous
  times match; otherwise keep separate (they may be genuinely different sessions).
- **Shared cohorts**: one session, `session_cohorts` = many (page cohort + listed cohorts). Never
  treat as duplicates or conflicts.

## 4.5 Validation taxonomy (applied at ingestion)

| Code | Meaning | Severity |
|---|---|---|
| `MISSING_CODE` | No course code recoverable | warn |
| `MISSING_VENUE` / `MISSING_LECTURER` | Field absent | info |
| `BAD_TIME` | Non-monotonic or non-standard slot | error |
| `OVERLAP_SAME_COHORT` | Two sessions overlap for the same cohort | error* |
| `OVERLAP_SHARED` | Overlap but explained by shared cohorts | info (not conflict) |
| `DUP_SESSION` | Same code+cohort+day+time twice | error |
| `UNKNOWN_TOKEN` | Unclassifiable line in a cell | warn |
| `LOW_CONFIDENCE` | Heuristic parse uncertain | warn (review required) |

`*` Overlaps are only errors when they cannot be explained by shared cohorts or electives.

## 4.6 Evaluation dataset & methodology

- Build a **gold set** of ~25 pages (≈300 sessions) manually transcribed and verified by the
  product owner/DIT from rendered page images.
- Measure:
  - **Field-level accuracy** per field (code, cohort, day, start, end, venue, lecturer).
  - **Complete-session accuracy** (all fields correct) — the headline metric.
  - **Uncertainty rate** (records flagged low-confidence) — reported separately, never counted as
    correct by default.
- Run the naive baseline (`tools/discovery/extract_sessions.py`) on the gold set first.

## 4.7 Success criteria (to be ratified after the gold-set baseline)

| Metric | Target (proposed) |
|---|---|
| Course code accuracy | ≥ 98% |
| Cohort + day accuracy | ≥ 99.5% |
| Time-range accuracy | ≥ 99% |
| Complete-session accuracy | ≥ 95% |
| Silent-wrong rate (published errors) | **0** — uncertain records must be flagged, never auto-published |

## 4.8 PoC deliverables

1. Gold set (JSON + page images) and a scoring script.
2. Geometry parser prototype + naive-extractor comparison table.
3. Documented list of residual hard cases + fallback behaviour.
4. Go/No-Go recommendation with measured numbers.
