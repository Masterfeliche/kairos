# 6. System Architecture

## 6.1 Recommended stack (validated against discovery)

The proposed stack is appropriate, with a few clarifications:

| Layer | Choice | Notes |
|---|---|---|
| Frontend | Next.js + React + TypeScript + Tailwind | SSR for fast first paint; typed API client |
| Backend API | Python + FastAPI | Shared language with the parser (PyMuPDF/pdfplumber) |
| PDF parsing | PyMuPDF (geometry) + pdfplumber (fallback) | OCR **not needed** (text layer present) |
| Database | PostgreSQL | Partial unique index enforces one active version |
| Object storage | S3-compatible (or local disk on the VM) | Immutable source PDFs + rendered page images |
| Background jobs | **Postgres-backed job runner** (e.g. RQ/arq with a small worker) | Justified: extraction is slow and must not block the API |
| Auth | Single admin realm (JWT/session) | Students have no accounts |
| Deployment | One VM (Docker Compose) + managed Postgres, or a small PaaS | Not microservices |

**Simplification vs the brief:** a full external queue (RabbitMQ/SQS) is unnecessary for the MVP.
One worker process consuming jobs from a Postgres table is enough and is easier to operate.
Introduce a real broker only when throughput demands it.

## 6.2 Components

```
              ┌────────────────────────┐         ┌───────────────────────────┐
  Browser  ──▶│ Next.js (student + admin│──HTTP──▶│ FastAPI application       │
  (mobile)    │ UI, SSR, typed client)  │         │ - public read API         │
              └────────────────────────┘         │ - admin write API (auth)  │
                                                 │ - upload + job enqueue    │
                                                 └───────┬───────────┬───────┘
                                                         │           │
                                         ┌───────────────▼──┐   ┌────▼──────────────┐
                                         │ PostgreSQL       │   │ Object storage    │
                                         │ staging+published│   │ PDFs, page images │
                                         └─────────┬────────┘   └───────────────────┘
                                                   │
                                         ┌─────────▼─────────┐
                                         │ Extraction worker │  PyMuPDF/pdfplumber
                                         │ (jobs table poll) │  → normalise → validate
                                         └───────────────────┘
```

| Component | Responsibility |
|---|---|
| Next.js app | Student browsing (SSR/ISR reads), admin console (client), no PDF logic |
| FastAPI public API | Read-only timetable endpoints; strict caching; no secrets |
| FastAPI admin API | Auth, upload, import control, review, publish, rollback, audit |
| Extraction worker | Runs the pipeline; writes **staging only**; cannot publish |
| PostgreSQL | All structured data + job queue + audit |
| Object storage | Immutable PDFs + page images used as review evidence |

## 6.3 Ingestion data flow

```
upload ─▶ validate (type/size/encryption) ─▶ store immutable (hash) ─▶ import_job(queued)
   └─▶ worker: classify pages → geometry parse → normalise → validate
        → write draft timetable_version + sessions + validation_issues (status=review)
   └─▶ admin reviews (evidence images) → corrections → compare vs active version
        → approve ─▶ single transaction: activate new version, supersede old (status=published)
```

Admin-triggered steps are **idempotent**: re-running an import for the same source hash either
resumes or is refused; publishing the same version twice is a no-op.

## 6.4 Publication design (atomic, safe)

- One **partial unique index** guarantees a single active published version per period.
- Publish runs in one DB transaction with `SELECT ... FOR UPDATE` on the period's active version:
  1. verify the draft is `review` and has no blocking (`error`) issues,
  2. set old active → `superseded`,
  3. set new → `published`, `is_active = true`,
  4. write `publication_record` + `audit_event`.
- **Rollback** = re-publish a previous version (new `publication_record` with action=rollback).
  No data is deleted.
- **Concurrent imports**: per-period lock; second concurrent publish attempt is rejected or queued.
- **Failed import** leaves staging rows discarded and the active version untouched.

## 6.5 API boundaries

| Boundary | Rule |
|---|---|
| Public | Only published, active-version data; aggregate/normalised fields; no raw cells |
| Admin | Authenticated + role-checked; can read staging, evidence, audit |
| Worker | DB-only; no public network; writes staging only |
| Storage | PDFs served only to admins via short-lived signed URLs (or proxied) |

## 6.6 Auth & authorisation

- Student side: **no accounts**.
- Admin: email + password (hashed with Argon2/bcrypt), HTTP-only session cookie or short-lived JWT,
  roles `reviewer` (correct/annotate) and `owner` (publish/rollback/users).
- All admin mutations require CSRF protection (same-site cookies) and are audit-logged.

## 6.7 File validation

- Accept only `application/pdf`; verify magic bytes `%PDF-`.
- Max size (proposal 50 MB), max pages (proposal 1,000).
- Reject encrypted/password-protected files; reject files with embedded JavaScript.
- Compute SHA-256; refuse duplicate upload of an already-imported document (unless forced).
- Render/parse in a constrained worker (resource limits, timeout).

## 6.8 Database transactions & integrity

- Extraction writes in batched transactions per page or per version (resumable).
- Publishing is the only step that touches active data, and it is atomic.
- All writes use server-side timestamps and FK constraints; `session_cohorts` uses a composite PK.

## 6.9 Deployment, monitoring, backup, recovery

- Docker Compose: `web` (Next.js), `api` (FastAPI), `worker`, `db` (or managed), `minio`/disk.
- Health endpoints (`/healthz`, `/readyz`); structured JSON logs with request IDs; no secrets logged.
- Metrics: request latency, job duration/failures, validation-issue counts, publish events.
- Backups: nightly Postgres dumps + object-storage versioning; documented restore + tested quarterly.
- Recovery targets (proposal): RPO 24 h, RTO 4 h. **[OPEN]**

## 6.10 What we deliberately avoid

- No microservices, no service mesh, no Kafka, no Kubernetes for MVP.
- No separate search cluster (Postgres FTS or simple ILIKE over a small dataset).
- No ML model until the rule/geometry parser is proven insufficient.
