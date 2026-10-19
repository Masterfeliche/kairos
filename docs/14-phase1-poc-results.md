# 14 — Phase 1 Extraction PoC: Results

Status: prototype complete; **not production-ready**. This document records the
measured outcome of the Phase 1 Proof of Concept and the recommendation that
follows. No application code was written in Phase 1 (by design).

## 1. Objective

Prove that the official DIT timetable PDF can be extracted into structured
sessions with enough accuracy to be worth building the website, and quantify the
remaining error so the admin-review step can be sized.

## 2. What was built

| Artifact | Purpose |
| --- | --- |
| `tools/discovery/extract_sessions.py` | Naive baseline: `pdfplumber.extract_tables` per page × cohort. |
| `tools/poc/geometry_parser.py` | Geometry-first prototype: rebuild the grid from vector rules, assign words by coordinate, reassemble cells, parse codes, detect shared cohorts. |
| `tools/poc/compare.py` | Agreement between the two strategies. |
| `tools/poc/score.py` | Accuracy against the candidate gold set. |
| `data/fixtures/gold/gold_pages.json` | 29 human-transcribed sessions on pages 2, 3, 147. |

## 3. Measured results

Run: `python tools/poc/geometry_parser.py` then `python tools/poc/score.py poc_sessions.json`.

### 3.1 Whole-document totals

| Metric | Naive baseline | Geometry prototype |
| --- | --- | --- |
| Sessions | 1810 | 1912 |
| With course code | 1810 | 1820 |
| Without course code | 123 cells | 92 cells |
| Shared-cohort cells | 15 | 16 |
| Source pages | 160 | 160 |

Session duration is derived from the **per-column hour span**: horizontal grid lines
are emitted as thin rectangles whose x-span shows where a column's cell is vertically
merged. A cell covering N hour labels is an N-hour session. Distribution:
1 h = 50, 2 h = 792, 3 h = 834, 4 h = 236. (Method is confirmed by the owner:
"measure a column from the hours … if it takes more hours it's a multi-hour session";
matches decision O2. Visual spot-check still advised — see §7.)

### 3.2 Agreement (page, day, start, code)

- Naive codes: 1810 · Geometry codes: 1820
- **Agree: 1763** (96.9% of geometry, 97.4% of naive)
- Geometry-only: 57 · Naive-only: 47

Disagreement is concentrated on a few unusual pages:

```
naive-only by page: {16:2, 26:2, 74:17, 86:11, 87:1, 93:5, 94:8, 133:1}
geom-only  by page: {16:1, 63:8, 64:8, 65:8, 69:3, 70:3, 71:3, 74:13, 86:9, 87:1}
```

(The 63–71 geometry-only recoveries are `G`-prefixed codes such as `EET G4202`
that the naive baseline's code pattern cannot match.)

Pages 74 (continuation of `BT23LS-1`), 86, 93–94 (masters/evening layouts) are
where the two strategies diverge. Neither can be trusted there without visual
confirmation.

### 3.3 Gold-set accuracy (candidate gold, 29 sessions)

| Metric | Value |
| --- | --- |
| Gold sessions | 29 |
| Matched (page/day/time) | 29 / 29 |
| Course code correct | 29 / 29 |
| **Code accuracy** | **100%** |
| Recall vs gold | 100% |
| Unexpected extras | 0 |

The gold set also caught two real transcription traps: page 3 is *not* empty
(8 late-evening sessions) and page 147's shared `(L)` session is on **Tuesday**,
not Wednesday. Both times the geometry parser had the PDF right and the first
human draft was wrong.

## 4. Defects found and fixed during the PoC

1. **Phantom footer sessions** — the footer `Timetable generated on 10/3/26 1:08 PM`
   was being sliced into a cell as `1:08 PM`, creating ~156 fake sessions. Fixed
   with a y-coordinate footer cutoff in `geometry_parser.py`. This is what brought
   the geometry session count from 2069 down to 1912.
2. **Schema drift** between the two scripts (`code`/`slot` vs `course_code`/`start_time`)
   — normalised in `compare.py`/`score.py`.
3. **`G`-prefixed codes** (`GST G6107`, `EET G4202`) were not matched, so 33 sessions
   on pages 63–71 came back `MISSING_CODE`. Widened `CODE_PAT` to accept an optional
   letter before the digits (owner confirmed these are real course codes).
4. **Multi-hour duration** was hard-coded to one hour. Now derived from the column's
   hour span (§3.1).

## 5. Remaining hard cases (carried into Phase 2)

- **Continuation / landscape pages** (74–75): different column geometry, truncated
  day headers ("Frid"), no repeated cohort header. Current handling by carrying the
  cohort forward is fragile.
- **Masters / evening elective layouts** (86, 93–94): different cell density and
  code formats that surface as `MISSING_CODE`.
- **Text-overflow spill**: the geometry repair pass currently finds **0** recoverable
  cases because, in the PDF, the code fragment `(CODE` is almost never at the end of
  a cell's text — lecturer/venue follow it. Correct behaviour is to **flag**, not
  fabricate; these are the cells containing an incomplete `(CODE`.
- **Multi-hour / merged cells**: duration now comes from the per-column hour span
  (§3.1); `multi_row_band` is retained as an audit flag.

## 6. Recommendation

1. **Do not ship either parser as-is.** Accuracy is high on standard cohort pages
   but unverified on continuation/masters pages.
2. **Build on the geometry parser**, not the naive one, because it is robust to the
   wrapped-code spill that defeats `extract_tables`, and it handles shared cohorts.
3. **Adopt a hybrid cell reader** in Phase 2: use the geometric grid for the
   day/column/time assignment, but read complete cell text from the text layer so
   wrapped codes are rejoined without column-band guesswork.
4. **Keep mandatory admin review.** Every `MISSING_CODE`, `multi_row_band`, and
   continuation/masters page must be surfaced for human confirmation before publish.
5. **Grow the gold set with visual verification** to cover pages 74–75, 86, 93–94
   and at least one spill/multi-hour case before the accuracy gate (≥95%
   complete-session accuracy) can be certified.

## 7. Questions for the product owner

- Can DIT (or you) visually confirm pages **74–75, 86, 93–94** — specifically the
  day/column mapping and which tall rows are single multi-hour sessions?
- ~~Are the `GST G6107` / `EET G4202`-style codes real?~~ **Resolved: yes, they are
  real codes** (owner, Phase 1 review). The parser now accepts them.
