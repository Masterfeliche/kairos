# 16. Phase 3 - Admin console

Status: **implemented** (backend + admin UI). This document records what was built, how it maps to
`docs/06-ux-specification.md` and `docs/07-api-specification.md`, and what remains.

## 16.1 Goal

An administrator (role `reviewer`) can import a timetable PDF, review the extracted sessions
against the rendered source page, correct fields, and an `owner` can atomically publish or roll
back a version - **using only the UI**. Every mutation is written to an append-only audit trail.

## 16.2 Components

### Backend (FastAPI) - `backend/app/`

| Area | Module | Notes |
|---|---|---|
| Password hashing / tokens | `core/security.py` | Argon2id; session tokens stored only as SHA-256 hashes |
| Admin accounts & sessions | `models/entities.py` (`AdminUser`, `AdminSession`), `services/auth_service.py` | 8 h sessions, revocation, `last_login_at` |
| Auth endpoints | `api/admin_auth.py` | login / logout / me; in-process login throttle (5 / 5 min / IP) |
| Auth deps | `api/deps.py` | `get_current_admin`, `require_owner`, double-submit `verify_csrf`, `client_ip` |
| Audit trail | `services/audit_service.py`, `models.AuditEvent` | actor, action, entity, before/after JSON, IP |
| Corrections | `services/correction_service.py` | field-level edits + mandatory reason; writes `SessionFieldEvidence`; auto-resolves `MISSING_CODE` |
| Version diff | `services/diff_service.py` | keyed by `session_identity_key`; added / removed / changed |
| Evidence images | `services/rendering.py` (`render_page_bytes`) | on-demand PNG of a source page |
| Admin API | `api/admin.py` | imports, versions, review, corrections, diff, publish/rollback, history, audit |
| CLI | `app/cli.py` | `create-admin <email> [--role owner] [--password ...]` |
| Migration | `migrations/versions/a1f2c3d4e5b6_admin_auth.py` | `admin_user`, `admin_session`, `audit_event.actor_id` |

### Frontend (Next.js App Router, TypeScript, Tailwind) - `frontend/`

| Route | File | Purpose |
|---|---|---|
| `/admin/login` | `app/admin/login/page.tsx` | sign in |
| `/admin` | `app/admin/page.tsx` | version list (status, active) |
| `/admin/imports` | `app/admin/imports/page.tsx` | upload + extraction + job history |
| `/admin/versions/[id]` | `app/admin/versions/[id]/page.tsx` | review queue + source-page image + inline correction editor + publish/rollback + issue resolution |
| `/admin/versions/[id]/diff` | `app/admin/versions/[id]/diff/page.tsx` | added / removed / changed vs active |
| `/admin/history` | `app/admin/history/page.tsx` | publication history |
| `/admin/audit` | `app/admin/audit/page.tsx` | audit log |

`components/AdminShell.tsx` provides the authenticated layout and nav; it redirects to
`/admin/login` on `401`. `lib/api.ts` is the fetch wrapper (credentials + CSRF header).

`next.config.mjs` rewrites `/api/:path*` to the backend (`TT_BACKEND_ORIGIN`, default
`http://localhost:8000`) so browser requests are same-origin and HttpOnly cookies work.

## 16.3 Admin API (base `/api/v1/admin`)

| Method | Path | Role | Notes |
|---|---|---|---|
| POST | `/auth/login` | - | sets `tt_session` (HttpOnly) + `tt_csrf` cookies |
| POST | `/auth/logout` | any | CSRF required |
| GET | `/auth/me` | any | current admin |
| POST | `/import` | any | multipart; magic-byte, size, JS/encryption checks; SHA-256 dedupe unless `force` |
| GET | `/versions` | any | |
| GET | `/versions/{id}` | any | counts: sessions, open issues, open errors, pages |
| GET | `/versions/{id}/issues` | any | `include_resolved` |
| GET | `/versions/{id}/sessions` | any | `page`, `size`, `q`, `only_issues` |
| POST | `/sessions/{id}/correct` | any | `{changes, reason}`; CSRF |
| POST | `/issues/{id}/resolve` | any | CSRF |
| GET | `/versions/{id}/diff` | any | `base` optional |
| GET | `/versions/{id}/pages/{page}.png` | any | source-page evidence |
| POST | `/versions/{id}/publish` | **owner** | CSRF; blocked while error issues remain |
| POST | `/periods/{id}/rollback/{version_id}` | **owner** | CSRF |
| GET | `/jobs`, `/history`, `/audit`, `/source-documents` | any | |

## 16.4 Security model

- **Accounts**: `reviewer` / `owner` (and `admin`) roles; Argon2id hashes; disabled accounts rejected.
- **Session**: random token in `tt_session` cookie (`HttpOnly; SameSite=Lax`; `Secure` when
  `TT_SECURE_COOKIES=true`); server stores only `sha256(token)`; logout revokes.
- **CSRF**: double-submit - readable `tt_csrf` cookie must match the `X-CSRF-Token` header on every
  state-changing request.
- **Upload**: `%PDF-` magic bytes, 50 MB cap, rejects `/JavaScript`, `/Launch`, `/Encrypt`.
- **Publish**: owner-only; refuses while unresolved `error`-severity issues exist.
- **Audit**: `auth.login`, `import.create`, `session.correct`, `issue.resolve`, `version.publish`,
  `version.rollback` recorded with actor + IP.

## 16.5 Verification

- `python -m pytest` - 21 tests (extraction, import, publish, api, admin auth/CSRF/corrections/audit/roles).
- Alembic `upgrade head` + `downgrade base` verified on a fresh SQLite DB (20 tables).
- `npm run build` - Next.js production build succeeds.
- End-to-end smoke: Next.js proxy -> `/auth/login` (200, cookies) -> `/auth/me` (owner) -> `/versions`.

## 16.6 Remaining / follow-ups

- MFA for `owner` is still **[OPEN]** (`docs/08` §9.1).
- Background job runner: import runs inline in the request; move to a queue for large PDFs
  (`docs/05` §6.7). Job rows already model status/progress.
- MFA, per-endpoint rate limiting beyond login, and DB-backup runbook remain ops tasks.
- Evidence-page access for lecturers is admin-only by design (privacy, `docs/08` §9.5).
