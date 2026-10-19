# 11. Implementation Roadmap

Phased, small increments. Each milestone lists deliverables and a Definition of Done (DoD).

## Phase 0 — Discovery & Validation (done)
- **Deliverables:** all planning docs; reproducible discovery scripts; PoC plan; introductory PDF
  inspection results.
- **DoD:** product owner has reviewed findings and answered the blocking Open Decisions (artifact 12).
  ✅ **Met.**

## Phase 1 — Extraction Proof of Concept (done)
- **Tasks:** build gold set (~25 pages / 300 sessions); implement geometry parser prototype; compare
  with naive baseline; produce scoring script + accuracy report; document residual hard cases.
- **Deliverables:** re-runnable parser PoC, gold JSON + page images, PoC report with measured numbers.
- **Dependencies:** Phase 0 approval on semantics (`-x-`/`---`, multi-hour encoding).
- **DoD:** complete-session accuracy measured; silent-wrong = 0; Go/No-Go recorded.
  ✅ **Met** — 29/29 gold sessions correct (100%), Go recorded in `docs/14-phase1-poc-results.md`.
  (Open: visual confirmation of pages 74–75, 86, 93–94 → O15.)

## Phase 2 — Core data model & import pipeline (done)
- **Tasks:** Postgres schema + migrations; entity models; import_job worker; extraction →
  normalisation → validation writes to staging; page-image rendering.
- **Deliverables:** working CLI/API import producing a `draft` version with issues.
- **Dependencies:** Phase 1 parser.
- **DoD:** importing the real PDF creates a complete draft; failed import leaves DB clean;
  unit + integration tests green.
  ✅ **Met** — `backend/` with SQLAlchemy models, Alembic migration, geometry extraction library,
  atomic import + publish/rollback services, FastAPI public/admin routers, CLI, and passing tests.
  Real-PDF import yields 1912 sessions / 1820 with code / 175 issues.
  (Background worker loop deferred to Phase 5; auth-gated admin flow delivered in Phase 3.)

## Phase 3 — Admin console (done)
- **Tasks:** auth + roles; upload UI; job status; review UI with source-page evidence; corrections;
  version diff; atomic publish + rollback; history + audit log.
- **Deliverables:** end-to-end admin workflow to publish a version.
- **Dependencies:** Phase 2.
- **DoD:** an admin can import → review → correct → publish → rollback using only the UI; all
  publish/rollback integration tests green; audit log populated.
  ✅ **Met** — Argon2id auth + `reviewer`/`owner` roles, session cookies + CSRF, audit trail,
  review/correction APIs with rendered source-page evidence, version diff, owner-gated atomic
  publish/rollback, and the Next.js console (`frontend/`). 21 backend tests green; Next.js build
  passes; proxy smoke test verified. See `docs/15-phase3-admin-console.md`.
  (Remaining: MFA for owner — `docs/08` §9.1 [OPEN].)

## Phase 4 — Student website (core done)
- **Tasks:** programme/cohort selection; Today + Week views; session detail; remembered selection;
  last-updated + version banner; empty/error states; a11y + performance.
- **Deliverables:** responsive student site against the published version.
- **Dependencies:** Phase 3 (a published version must exist); public read API.
- **DoD:** full student journey passes E2E on 360 px; Lighthouse ≥ 90; axe = 0 critical.
  ◐ **Core implemented** — server-rendered `/`, `/c/[cohort]` (Today + Week), `/about`, 404;
  public `/programmes` + rich `/timetable`; dev-only draft preview. Next.js build passes and
  `OD24COE-1` renders. **Lighthouse ≥ 90 + axe 0 critical certified on the production build**
  (see `docs/16-phase4-student-site.md` §17.6). Remaining: 360 px visual pass.

## Phase 5 — Hardening & launch
- **Tasks:** rate limiting, monitoring, backups + restore drill, retention policy, docs/runbooks,
  security review, load check with realistic sizes (160 pages / ~1,900 sessions).
- **Deliverables:** production deployment + runbooks.
- **Dependencies:** Phases 3–4.
- **DoD:** release gates G1–G5 (artifact 10) all met.

## Phase 6 — Post-MVP (optional)
- Notifications, calendar export, additional periods/institutions, lecturer corrections.

## Cross-cutting tasks (every phase)
- CI (lint, type-check, tests), migration discipline, changelog, ADRs for decisions.

## Sequencing / dependencies
```
Phase0 ──▶ Phase1 ──▶ Phase2 ──▶ Phase3 ──▶ Phase4 ──▶ Phase5
                     (parser)   (admin)    (student)   (harden)
```
Do **not** start Phase 4 UI before Phase 1 proves extraction quality; otherwise the data model and
display assumptions may be wrong.
