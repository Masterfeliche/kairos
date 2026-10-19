# 13. Open Decisions (need product owner / DIT confirmation)

Blocking items must be answered before Phase 1 can be completed. Non-blocking items can be answered
during Phases 2–3.

## Resolved (confirmed by product owner)

| # | Question | Decision (confirmed) |
|---|----------|----------------------|
| O1 | `-x-` / `---` semantics | **`-x-` = blocked/not available**, **`---` = free period** |
| O2 | Multi-hour representation | **Merged/taller row = one session** |
| O3 | Two-digit cohort number | **Intake year** (`24` → 2024 intake) |
| O4 | Academic period label | **2025/2026, Semester I** (title "2026-2025" treated as a typo) |
| O5 | Accuracy target / review model | ≥95% complete-session; admin review required before publish |
| O6 | Evening/weekend classes | Include `19:00–21:00` as-is; no weekend columns |
| O-Approval | Proceed to Phase 1 PoC | **Approved** |

## Resolved during Phase 1 PoC

| # | Question | Decision |
|---|----------|----------|
| P1 | Footer `Timetable generated on …` treated as content? | **No — it is a page footer.** Filter by y-coordinate; never emit as a session. |
| P2 | Recover spilt wrapped codes by auto-repair? | **No fabrication.** Flag cells with an incomplete `(CODE` as `MISSING_CODE` for admin review. |
| P3 | Which parser to build Phase 2 on? | **Geometry-first** (robust to code spill + shared cohorts), with a hybrid full-cell text reader. |
| P4 | Infer session duration from merged-row height? | **Duration = per-column hour span** (owner-confirmed, matches O2). A cell covering N hour labels is an N-hour session. |

## Blocking (before Phase 2 close) — need visual confirmation

| # | Question | Why it blocks |
|---|----------|---------------|
| O15 | Confirm day/column mapping and multi-hour rows for pages **74–75, 86, 93–94** | The two parsers disagree on these pages; ground truth is visual-only and cannot be self-verified. |
| O16 | ~~Are `GST G6107` / `EET G4202`-style codes real?~~ | **Resolved: real codes** (owner). Parser updated to accept `G`-prefixed codes. |


## Non-blocking (Phases 2–3)

| # | Question | Proposed default |
|---|----------|------------------|
| O7 | Is the venue free text acceptable, or is there a venue/room master list? | Store raw + optional normalised code |
| O8 | Is there a programme → department mapping we should use instead of inferring from codes? | Infer from code prefixes; refine later |
| O9 | Are `MASTERS-*`, `MC26SE`, `MT26CC`, `MTCC26-1` one programme each or cohorts of programmes? | Treat as cohorts; confirm grouping |
| O10 | Retention period for source documents and versions? | 3 academic years |
| O11 | Recovery targets (RPO/RTO) and hosting preference (self-hosted vs managed)? | RPO 24 h / RTO 4 h; managed DB |
| O12 | Should admin MFA be required? | Yes for `owner` role |
| O13 | Who are the initial admin users and what approval process governs publishing? | DIT Timetabling Office |
| O14 | Are there other timetable variants (e.g. by department, or a lecturers' copy) we must ingest? | Scope to the Students copy now |

## Decisions already fixed by us (reversible)

- Mobile-first **agenda** layout (not a squeezed 5×14 grid) with an optional desktop grid.
- Staging vs published separation; atomic publish; retained superseded versions.
- No student accounts; no OCR/ML in MVP.
- Postgres-backed job runner instead of an external broker.
