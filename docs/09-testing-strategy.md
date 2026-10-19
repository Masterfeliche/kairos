# 10. Testing Strategy

## 10.1 Test layers

| Layer | Scope | Tooling |
|---|---|---|
| Unit | Parser helpers, normalisation, validation rules, diff/identity key | pytest |
| Fixture / extraction | Representative PDF pages → expected sessions | pytest + gold JSON |
| Regression | All known layouts (L1–L5) stay correct across changes | pytest, parametrised |
| Integration | DB writes, staging→publish transaction, idempotency, rollback | pytest + test Postgres |
| API | Contracts, auth matrix, error formats, rate limits | FastAPI TestClient |
| Frontend | Components, selection flow, week view, a11y | Vitest + Testing Library |
| E2E | Student journey + admin import→review→publish | Playwright (mobile viewport) |
| Security | Upload validation, authz, CSRF, malicious PDF fixtures | pytest |
| Performance | Realistic timetable payloads, slow-network budget | Lighthouse / k6 (light) |
| Accessibility | Contrast, keyboard, semantics | axe-core |

## 10.2 Extraction fixtures (from real pages)

| Fixture | Page | Asserts |
|---|---|---|
| `p01_beng23bebe` | 1 | wrapped codes recovered, lecturer/venue split |
| `p02_beng23ce` | 2 | standard grid |
| `p03_blocked` | 3 | all `-x-` → zero sessions, empty state |
| `p42_codespill` | 42 | `(CSEU` + `07102)` rejoined (the key regression) |
| `p74_continuation` | 74–75 | cohort carried across pages |
| `p93_masters_electives` | 93 | shared cohorts in electives |
| `p147_shared` | 147 | `OD26CST-1, OD26ERE-1` → one shared session |
| `p160_multitable` | 160 | two tables handled |
| `p37_artifact` | 37 | `--- -` not misread as a session |

Each fixture stores the expected sessions as JSON plus a rendered page image for human verification.

## 10.3 Gold set & metrics

- ~25 pages / ~300 sessions manually verified.
- Reported per run:
  - Field-level precision/recall/accuracy (code, cohort, day, start, end, venue, lecturer).
  - **Complete-session accuracy** (all fields correct).
  - Uncertain/flagged rate (reported separately).
  - **Silent-wrong count** (must be 0).

## 10.4 Key functional test cases

- Duplicate session detection (same code/cohort/day/time).
- Overlap detection: true conflict vs shared-cohort false positive.
- Missing identifiers flagged, not fabricated.
- Idempotent import of the same SHA-256.
- Failed import leaves active version unchanged.
- Atomic publish: old→superseded and new→published in one transaction.
- Rollback restores the previous version and is audited.
- Concurrent publish attempts: exactly one succeeds.
- Version diff classifies added/removed/changed correctly (field-level).
- Upload rejects: non-PDF, oversized, encrypted, JS-bearing.
- Authorization matrix enforced (reviewer cannot publish).
- Mobile layout: no horizontal scroll at 360 px; tap targets ≥ 44 px.

## 10.5 Release gates

Only **after** the PoC baseline is measured do we finalise numeric gates. Provisional gates:

| Gate | Criterion |
|---|---|
| G1 Extraction | complete-session accuracy ≥ 95%; silent-wrong = 0 on gold set |
| G2 Admin safety | every publish path is atomic; rollback verified in integration tests |
| G3 Security | upload/authz/CSRF tests green; no secrets in logs |
| G4 Student UX | E2E passes on 360 px; Lighthouse perf ≥ 90; axe = 0 critical |
| G5 Ops | backup + restore drill documented and executed once |

The published timetable must always be traceable to the approved source, and ambiguous records must
never silently become verified data — enforced by gates G1 and G2.
