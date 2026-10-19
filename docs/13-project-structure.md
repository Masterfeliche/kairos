# 14. Initial Project Structure

Proposed layout for the repository. The `backend/` tree and the `frontend/` admin console are
implemented (Phase 2 and Phase 3); `worker/` and `infra/` arrive in later phases as noted.

> Implemented in Phase 2: `backend/app/{core,models,schemas,services,extraction,api}`, `backend/cli.py`,
> `backend/migrations/` (Alembic). The `tools/poc` geometry parser was promoted into
> `backend/app/extraction/parser.py`.
>
> Implemented in Phase 3: `backend/app/{api/admin.py,api/admin_auth.py,api/deps.py}`,
> `backend/app/services/{auth_service,audit_service,correction_service,diff_service}.py`,
> migration `a1f2c3d4e5b6`, and the `frontend/` Next.js admin console.

```
smarttimetable/
├─ README.md
├─ docs/                          # planning artifacts (single source of truth)
│  ├─ 00-discovery-report.md
│  ├─ 01-product-requirements.md
│  ├─ 02-mvp-scope.md
│  ├─ 03-extraction-poc-plan.md
│  ├─ 04-data-model.md
│  ├─ 05-system-architecture.md
│  ├─ 06-ux-specification.md
│  ├─ 07-api-specification.md
│  ├─ 08-security-operations.md
│  ├─ 09-testing-strategy.md
│  ├─ 10-roadmap.md
│  ├─ 11-risk-register.md
│  ├─ 12-open-decisions.md
│  ├─ 13-project-structure.md
│  └─ adr/                        # Architecture Decision Records (Phase 2+)
├─ tools/
│  └─ discovery/                  # evidence scripts (present)
│     ├─ inspect_document.py
│     └─ extract_sessions.py
├─ data/
│  └─ fixtures/                   # gold-set pages + expected JSON (Phase 1)
├─ backend/                       # FastAPI + parser (Phase 2+)
│  ├─ app/
│  │  ├─ api/            (public + admin routers)
│  │  ├─ core/           (config, security, db session)
│  │  ├─ models/         (SQLAlchemy)
│  │  ├─ schemas/        (Pydantic)
│  │  ├─ services/       (import, publish, diff, audit)
│  │  └─ extraction/     (geometry parser, validators, normalisers)
│  ├─ migrations/        (Alembic)
│  ├─ tests/
│  └─ pyproject.toml
├─ worker/                       # background extraction worker (Phase 5)
├─ frontend/                     # Next.js (student site Phase 4 + admin console Phase 3)
│  ├─ app/               (student: /, /c/[cohort], /about | admin: /admin/*)
│  ├─ components/        (student/*, AdminShell)
│  ├─ lib/               (api client, server-api, student types)
│  └─ package.json
├─ infra/                        # docker-compose, deployment, backups (Phase 5)
└─ .github/workflows/            # CI (Phase 2+)
```

## Development workflow

1. **Docs first.** Requirements/decisions live in `docs/` and ADRs; no silent scope changes.
2. **Small, testable increments.** Each phase ends with measurable acceptance criteria (artifact 10).
3. **Evidence-based extraction changes.** Any parser change must pass all fixtures + gold set.
4. **Branching:** short-lived feature branches → PR with tests → review → merge.
5. **CI gates:** lint + type-check + unit/integration tests; extraction fixtures are mandatory.
6. **Migrations** are versioned (Alembic) and run with a backup on deploy.
7. **Conventional commits**; changelog updated per release.
8. **Definition of Done** per milestone (artifact 11) before moving on.

## Not doing yet

- No scaffolded frontend or backend code until the PoC (Phase 1) validates extraction.
- No infrastructure provisioning until Phase 5.
