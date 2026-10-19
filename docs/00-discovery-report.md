# 1. Discovery Report

**Source document:** `TEACHING TIMETABLE 2026-2025 - SEMESTER I - Students.pdf`
**Method:** Direct inspection with PyMuPDF (text, words, drawings) and pdfplumber (tables, cells).
Reproducible scripts: `tools/discovery/inspect_document.py`, `tools/discovery/extract_sessions.py`.

> Legend: **[FACT]** observed in the document · **[ASSUMPTION]** inferred, needs confirmation ·
> **[REC]** recommendation · **[OPEN]** unanswered question.

---

## 1.1 Document-level facts

| Property | Value |
|---|---|
| Pages | **160** [FACT] |
| Page size | 792 x 612 pt (landscape A4/US-Letter), rotation 0 on all pages [FACT] |
| Producer / Creator | Microsoft Excel 2016 [FACT] |
| Author | Moses Kaswa [FACT] |
| Created | 2026-10-11 15:35:54 +03:00 [FACT] |
| Running title | `TEACHING TIMETABLE 2026-2025 - SEMESTER 1` + `Students` [FACT] |
| Running footer | `Timetable generated on 10/3/26 1:08 PM` on 156/160 pages [FACT] |
| Text layer | **Selectable, vector text** (not scanned). No OCR required. [FACT] |

The title string literally reads "2026-2025"; the footer generation date is 2026-03-10. This is
almost certainly the academic year 2025/2026 rendered in an ambiguous order. **[OPEN]**

## 1.2 Page layout inventory

Every page is one timetable sheet for one class/cohort, in a single dominant layout:

```
+---------------------------------------------------------------------------------+
| Students | TEACHING TIMETABLE 2026-2025 - SEMESTER 1                            |
|                    DAR ES SALAAM INSTITUTE OF TECHNOLOGY (DIT)                  |
|                            <CLASS/COHORT ID>          e.g. BENG23BEBE-1         |
| +-----------+--------+--------+--------+--------+--------+                       |
| | time      | Monday | Tuesday|Wednesday|Thursday| Friday |  <- header row       |
| +-----------+--------+--------+--------+--------+--------+                       |
| |07:00-08:00| cell   | cell   | cell   | cell   | cell   |                       |
| |08:00-09:00| ...    | ...    | ...    | ...    | ...    |                       |
| |   ...     |        |        |        |        |        |                       |
| |20:00-21:00| ...    | ...    | ...    | ...    | ...    |                       |
+---------------------------------------------------------------------------------+
| Timetable generated on 10/3/26 1:08 PM                                          |
+---------------------------------------------------------------------------------+
```

### Page-layout classes observed

| ID | Layout | How many pages | Notes |
|----|--------|----------------|-------|
| **L1** | Standard class grid, Mon–Fri x (07:00→21:00) | ~155 | The default; header + time rows + footer |
| **L2** | Continuation / overflow page | 1 (p.75) | No header row; carries overflow cells from p.74 (`BT23LS-1`) — days reduced, header truncated (`Frid`) |
| **L3** | Empty/blocked sheet | 5 pages | No teaching sessions; cells are `-x-`/`---` (e.g. p.3 `BENG23CE-2` top rows all `-x-`) |
| **L4** | Multi-timetable page | 1 (p.160) | `extract_tables()` returns 2 tables; needs special handling |
| **L5** | Masters/electives pages | ~8 | Same grid but cells carry elective group labels and multiple shared cohorts (p.93 `MTCC26-1`) |

**[FACT]** 159 pages return exactly one table; 1 page returns two.

## 1.3 Identifiers: programmes, cohorts, years

**Class/cohort ID** appears near the top-centre of each page at y ≈ 74.9 pt. **[FACT]**

Detected identifier families and counts of distinct top-of-page IDs (154 distinct):

| Family | Distinct IDs | Examples | Meaning [ASSUMPTION] |
|--------|-------------|----------|----------------------|
| `BENG{23,24,25,26}<PROG>-<n>` | 14+16+22+21 | `BENG24CE-1`, `BENG23BEBE-1` | BEng, intake year, programme, section |
| `BT{23,24,25,26}LS-<n>` | 1+2+3+3 | `BT25LS-3` | Bachelor of Technology, Laboratory Science |
| `OD{24,25,26}<PROG>-<n>` | 16+22+27 | `OD26COE-1`, `OD25IT-2` | Ordinary Diploma, intake year, programme, section |
| `MASTERS-<PROG>` | 4 | `MASTERS-CS`, `MASTERS-SE`, `MASTERS-MM`, `MASTERS-ETE` | Postgraduate programmes |
| `MC26SE`, `MT26CC`, `MTCC26-1` | 3 | — | Additional postgraduate/cross-cutting codes [OPEN] |

Programme tokens inside BENG IDs: `CE, COE, EE, ETE, ME, MNE, OG, BEBE` (Civil, Computer, Electrical,
Electronics, Mechanical, Mining, Oil & Gas, Biomedical). OD programme tokens: `AUTO, BEE, BIT, CE,
COE, CST, EE, ERE, ETE, FST, IT, ME, MFT, MNE, SLT`.

**[ASSUMPTION]** The two-digit number is the **intake/cohort year** (23→2023 etc.), *not* year of
study, because IDs for 23/24/25/26 all coexist in the same semester file. **[OPEN]** confirm.

**[FACT]** A single PDF page maps to exactly one cohort (except shared-class cells, §1.5), so the
navigation unit is **(programme → cohort)**.

## 1.4 How timetable content is represented [FACT]

- **Days**: header row columns `Monday`…`Friday` (5 columns). Saturday/Sunday not present.
- **Time slots**: left column labels `07:00-08:00` … `20:00-21:00` (14 slots). Some sheets start later.
- **A non-empty cell** typically contains, on separate lines:
  1. Course title (may wrap over 1–3 lines)
  2. `(<CODE> <number> ) <DEPT>` e.g. `(CEU 08109) CIVIL`
  3. Lecturer name(s) (may be several, comma-separated, e.g. `Dr. MALISA Johnson, KASWA Moses`)
  4. Venue code/name e.g. `CEITT1-C4`, `TT3-1`, `R-G4`, `W15-4`, `Rafic- F1-9 (Analog electronics lab)`
- **Placeholders**: `---` (3,450 cells) = free/no class; `-x-` (3,098 cells) = blocked/unavailable
  period. **[OPEN]** confirm exact semantics of each.
- **Practical/Lecture markers**: suffixes `-P` / `-L` and `(P)` / `(L)` after the course code.
- **Department tokens** after the code: `CS, CIVIL, GS, EE, LS, Mech`, plus `Civil_Geo`,
  `ME26MM-Elective- EE`, etc.

44 distinct course-code prefixes appear (e.g. `GST, COU, ETU, CEU, MET, ITT, CET, EEU, EET, LSU,
GSU, ETT, MEU, SLT, ...`). These are strong department/course-family signals.

## 1.5 Difficult cases (evidence)

1. **Course-code wrap spill (highest impact).**
   When a title is long, the opening `(CODE` and its digits land on different lines and even in
   *different detected cells*. Example, page 42:
   - Words: `(CSEU` at x≈526, `07102)` at x≈549; a second `07102)` at x≈649.
   - Both pdfplumber and PyMuPDF table extraction return `Computer Programming Fundamentals (CSEU`
     **without the number**, i.e. ~6% of cells (123/1933) lose the code.
   - **Cause:** wrapped tokens cross column boundaries; cell-scoped extraction drops or misroutes them.

2. **Column/day misalignment on merged rows.**
   Ruling horizontal lines are not equally spaced (row heights grow with content, e.g. page 42 row 8
   spans y 167.8–260.7 while others are ~10.4 pt). Table extractors sometimes merge different
   numbers of rows per column, which can shift day assignment. Geometry confirms real day columns at
   x ≈ 51 (time), 108 (Mon), 210 (Tue), 323 (Wed), 460 (Thu), 598 (Fri), 735 (right edge).

3. **Multi-hour sessions.**
   Only **13** adjacent cells in the whole document repeat the same course code across consecutive
   slots. So multi-hour sessions are *not* generally stored as repeated cells; they appear to be
   represented as **merged/taller rows** spanning slots. **[ASSUMPTION]** confirm against visuals.

4. **Shared / combined classes.**
   Cells explicitly list multiple cohorts, e.g. `BENG24MNE-1, BENG23OG-1`, `OD26CST-1, OD26ERE-1`,
   `OD26ETE-1, OD26AUTO-1`, `BENG24EE-1, BENG24EE-2`, and on p.93 several `MASTERS-CS` electives
   reference `MTCC26-1`. 15 such references detected. These are **intentional shared sessions**, not
   scheduling conflicts.

5. **Continuation pages** (p.75) have no header row and truncated day labels (`Frid`); the previous
   page's cohort must be carried forward.

6. **Footer text inside the table grid** can leak into the last cell (`Timetable generated on ...`).

7. **Odd artifacts**: a cell rendering as `--- -` (p.37); title truncation on p.93 header.

## 1.6 What is absent or ambiguous

| Item | Status |
|---|---|
| Venue type/normalization (room vs lab) | Absent — venues are free text [OPEN] |
| Lecturer identity (unique ID) | Absent — names only, variable formats [OPEN] |
| Course full title vs abbreviations | Inconsistent wrapping [FACT] |
| Semester end/start dates, academic calendar | Absent [OPEN] |
| Week-parity (odd/even week) or date ranges | Absent [OPEN] |
| Room capacity / building | Absent [OPEN] |
| Explicit programme → department mapping | Absent — infer from code prefixes [OPEN] |
| Meaning of `-x-` vs `---` | Ambiguous [OPEN] |
| Multi-hour duration encoding | Ambiguous (merged rows) [OPEN] |
| Historic/revision policy | Not encoded in the file [OPEN] |

## 1.7 Extraction method recommendation (evidence-based)

Because the PDF contains a clean text layer with vector rules, **OCR is not needed**. Recommended
per page type:

| Page type | Method |
|---|---|
| L1/L3/L5 standard grids | **Geometry-first reconstruction**: detect vertical rules (day columns) and horizontal rules (time rows), assign words to cells by coordinates, then reassemble lines. This avoids code-spill and merge misalignment. |
| L2 continuation | Carry forward cohort from previous page; same geometry method |
| L4 multi-table | Split by detected tables; process each independently |
| Any page failing geometry checks | Fall back to `pdfplumber.extract_tables()` **and** cross-check against word geometry; flag low-confidence cells for admin review |

**Do not** rely on a single off-the-shelf table extractor. The PoC (artifact 4) must compare
(a) pdfplumber tables, (b) PyMuPDF `find_tables`, and (c) geometry-based word clustering, and
measure field-level accuracy against a manually verified gold set.

## 1.8 Provisional extraction statistics (naive baseline)

- Time-slot cells examined: **10,963**
- Non-empty teaching sessions found: **1,933**
- Sessions with a recoverable course code: **1,810 (~93.6%)**
- Cells missing a code (wrap spill / genuinely missing): **123 (~6.4%)**
- Placeholders: `---` 3,450 · `-x-` 3,098
- Pages with ≥1 session: 155 · pages with none: 5

These numbers are the **baseline** for the PoC targets in artifact 4.

## 1.9 Findings that change the plan

1. Trailing/leading code spill means the pipeline needs a **geometry-repair pass** before validation.
2. **Shared sessions** must be modelled as one session with many cohorts (not duplicates/conflicts).
3. **Continuation pages** break the "one page = one cohort" assumption; page grouping is required.
4. Naive table extraction is *good but not sufficient*; the PoC must prove ≥ a defined accuracy
   before committing to the architecture.
