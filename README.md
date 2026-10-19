# DIT Smart Timetable

A production-minded MVP that turns the official Dar es Salaam Institute of Technology (DIT)
teaching timetable PDF into a searchable, mobile-friendly website, with a safe administrator
workflow for importing, reviewing and publishing revised timetables.

> Status: **Phase 3 — admin console.** Discovery/planning docs live in `docs/`; the extraction
> prototype is in `tools/poc/`; the backend service (models, migrations, import/publish pipeline,
> authenticated admin API, CLI) is in `backend/`; the Next.js admin console is in `frontend/`.

## Source document

- `TEACHING TIMETABLE 2026-2025 - SEMESTER I - Students.pdf` (160 pages, landscape A4, Excel 2016 export)

## Documentation (single source of truth)

| # | Artifact | File |
|---|----------|------|
| 1 | Discovery report | `docs/00-discovery-report.md` |
| 2 | Problem statement & product requirements | `docs/01-product-requirements.md` |
| 3 | MVP scope | `docs/02-mvp-scope.md` |
| 4 | Extraction proof-of-concept plan | `docs/03-extraction-poc-plan.md` |
| 5 | Data model | `docs/04-data-model.md` |
| 6 | System architecture | `docs/05-system-architecture.md` |
| 7 | UX specification | `docs/06-ux-specification.md` |
| 8 | API specification | `docs/07-api-specification.md` |
| 9 | Security & operational plan | `docs/08-security-operations.md` |
| 10 | Testing strategy | `docs/09-testing-strategy.md` |
| 11 | Implementation roadmap | `docs/10-roadmap.md` |
| 12 | Risk register | `docs/11-risk-register.md` |
| 13 | Open decisions | `docs/12-open-decisions.md` |
| 14 | Initial project structure | `docs/13-project-structure.md` |
| 15 | Phase 1 PoC results | `docs/14-phase1-poc-results.md` |
| 16 | Phase 3 admin console | `docs/15-phase3-admin-console.md` |
| 17 | Phase 4 student site | `docs/16-phase4-student-site.md` |
| 18 | Deployment (deploy.tz + Postgres) | `docs/17-deployment.md` |

## Discovery tooling

Reproduce the findings:

```powershell
pip install pymupdf pdfplumber pdfminer.six pillow
python tools/discovery/inspect_document.py
python tools/discovery/extract_sessions.py
```

## Phase 1 extraction PoC

```powershell
python tools/poc/geometry_parser.py            # -> poc_sessions.json
python tools/poc/compare.py <naive.json> poc_sessions.json
python tools/poc/score.py poc_sessions.json    # vs data/fixtures/gold/gold_pages.json
```

Results and limitations: `docs/14-phase1-poc-results.md`.

## Phase 2 backend (`backend/`)

Requires Python 3.11+ (tested on 3.14). From `backend/`:

```powershell
python -m pip install -e ".[dev]"
python -m alembic upgrade head          # create schema (preferred)
python -m app.cli create-admin admin@dit.ac.tz --role owner
python -m app.cli import "..\TEACHING TIMETABLE 2026-2025 - SEMESTER I - Students.pdf"
python -m app.cli list-issues <version_id>
python -m pytest
```

- Defaults to SQLite for zero-setup dev; set `TT_DATABASE_URL` to a Postgres DSN for
  production.
- Schema is managed with Alembic: `python -m alembic upgrade head`.
- API: `uvicorn app.main:app --reload` (public `/api/v1/*`, admin `/api/v1/admin/*`).

## Phase 3 admin console (`frontend/`)

The admin console is a Next.js (App Router) + TypeScript + Tailwind app. It proxies `/api`
to the backend so session cookies work same-origin.

```powershell
# terminal 1 (backend)
cd backend
python -m uvicorn app.main:app --reload --port 8000

# terminal 2 (frontend)
cd frontend
& "C:\Program Files\nodejs\npm.cmd" install
& "C:\Program Files\nodejs\npm.cmd" run dev      # http://localhost:3000/admin
```

Sign in with the admin created above, then import the PDF, review/correct sessions against the
rendered source page, inspect the version diff, and publish or roll back. Details and the API
surface: `docs/15-phase3-admin-console.md`.

## Phase 4 student site

Public, read-only, mobile-first (no login). Routes: `/` (choose programme/class), `/c/[code]`
(Today, plus `?view=week`), `/about`. Server-rendered; fetches the backend via `TT_API_BASE`.

If no version is published yet, set `TT_ALLOW_DRAFT_PREVIEW=true` on **both** the backend and the
frontend to preview the latest review version (dev/staging only — never in production). Details:
`docs/16-phase4-student-site.md`.

## Glossary

- **Programme**: an academic programme (e.g. BEng Civil Engineering).
- **Cohort / Class**: a specific intake section (e.g. `BENG24CE-1`).
- **Session**: one teaching event (one course, one day, one time range, one venue/lecturer).
- **Version**: one published timetable imported from one source PDF.
