# 9. Security & Operational Plan

## 9.1 Access control

- Students: no accounts, read-only published data.
- Admins: restricted accounts with Argon2id password hashing; roles `reviewer` and `owner`.
- Session cookie `HttpOnly; Secure; SameSite=Lax`; short expiry + rotation.
- MFA recommended for `owner`. **[OPEN]**

## 9.2 Upload & PDF safety

| Control | Rule |
|---|---|
| Content type | Reject unless `%PDF-` magic bytes present |
| Size limit | 50 MB (configurable) |
| Page limit | 1,000 pages |
| Encryption | Reject password-protected files |
| Active content | Reject PDFs with embedded JavaScript/launch actions |
| Duplicate | SHA-256 dedupe; explicit force required to re-import |
| Processing isolation | Parse in worker with CPU/memory/time limits; never execute content |
| Storage | Immutable object storage; only admins get short-lived signed URLs |

## 9.3 Application security

- Input validation on every endpoint (Pydantic models).
- Parameterised queries / ORM (no string SQL).
- Output encoding + strict CSP; no inline scripts.
- CSRF protection on all admin mutations.
- Rate limiting (public reads, admin login, uploads).
- Dependency scanning + pinned lockfiles in CI.
- Secrets via environment/secret manager; never logged.

## 9.4 Auditability

- Every admin mutation writes an `audit_event` (actor, action, entity, before/after, IP, time).
- Corrections record the field, old value, new value and reason.
- Publication and rollback are recorded with the actor and diff summary.
- Audit log is append-only.

## 9.5 Privacy

- No student personal data is collected (no accounts).
- Lecturer names are professional directory data embedded in the source document; display them as
  published, but restrict the admin evidence pages.
- If future features collect personal data, add a retention policy and consent basis. **[OPEN]**

## 9.6 Reliability & recovery

| Concern | Approach |
|---|---|
| Failed import | Staging discarded; active version untouched |
| Partial publish | Publish is one transaction; all-or-nothing |
| Concurrent publish | Per-period row lock; second attempt rejected (409) |
| DB backup | Nightly dump + PITR if managed; object storage versioning |
| Restore test | Quarterly drill; documented runbook |
| Targets | RPO 24 h, RTO 4 h (proposal) |
| Monitoring | Health/readiness, job failures, validation-issue spikes, publish events |
| Logging | Structured JSON, request IDs, no secrets/PII |

## 9.7 Operational risks & MVP mitigations

| Risk | Mitigation |
|---|---|
| Poor PDF extraction quality | Admin review gate; uncertainty flags; publish blocked on errors |
| Bad publish | Atomic publish + one-click rollback + retained versions |
| Abuse of upload endpoint | Auth + rate limit + size/type checks |
| Disk growth (PDFs/images) | Retention policy; compress page images; monitor |
| Single VM failure | Backups + simple redeploy runbook; upgrade path to managed services |
| Clock/serialisation errors | Server-side UTC timestamps; ISO-8601 in API |

## 9.8 Environments

- `dev` (local Docker Compose), `staging` (mirrors prod, test imports), `prod`.
- Seed data and test PDFs live only in dev/staging.
- Migrations versioned and run automatically on deploy with a backup first.
