# 8. API Specification

Base URL: `/api/v1`. JSON. All timestamps ISO-8601 with offset. Public endpoints are read-only and
cacheable; admin endpoints require authentication.

Legend: **P** public · **A** admin (authenticated).

## 8.1 Public endpoints

### `GET /api/v1/periods` — P
Active and past academic periods.
```json
[{ "id": "…", "year_label": "2025/2026", "semester": 1, "is_active": true }]
```

### `GET /api/v1/programmes?period_id=…` — P
```json
[{ "id": "…", "name": "BEng Civil Engineering", "level": "beng", "department": "CIVIL" }]
```

### `GET /api/v1/cohorts?programme_id=…` — P
```json
[{ "id": "…", "code": "BENG24CE-1", "intake_year": 2024, "section": "1" }]
```

### `GET /api/v1/cohorts/{code}/timetable?version=active` — P
Returns version metadata + sessions for the active (or requested) version.
```json
{
  "version": { "id": "…", "label": "Semester I — rev 2026-03-10",
               "published_at": "2026-03-10T13:08:00+03:00",
               "source": { "page_count": 160 } },
  "cohort": { "code": "BENG23CE-1" },
  "sessions": [
    { "id": "…", "day_of_week": 2, "start_time": "08:00", "end_time": "09:00",
      "course": { "name": "Solid Waste Management", "code": "CEU 08109" },
      "lecturer": "Dr. OBERLIN Aisa", "venue": "R1-1",
      "session_type": "lecture", "shared_with": [],
      "source_page": 2 }
  ]
}
```
- Missing fields are `null` (explicitly), never invented.
- `?day=2` optional filter; `?view=week|today|day`.

### `GET /api/v1/cohorts/{code}/sessions/{id}` — P
Single session detail incl. all fields + provenance footnote.

### `GET /api/v1/search?cohort=&q=` — P (should-have)
Search course/lecturer/venue within a cohort.

### `GET /api/v1/meta` — P
Last-updated indicator data: active version label + published_at + document name.

## 8.2 Admin endpoints

### Authentication
- `POST /api/v1/admin/auth/login` — A (public route) → sets HTTP-only session cookie / returns token.
- `POST /api/v1/admin/auth/logout`
- `GET  /api/v1/admin/me`

### Imports
- `POST /api/v1/admin/imports` — A
  multipart upload (`file`) + `period_id`, `label`, optional `notes`.
  Validates type/size/hash, stores immutably, creates `import_job` (status `queued`).
  `202 Accepted` → `{ "job_id": "…", "version_id": "…" }`
  409 if the same document hash was already imported.
- `GET  /api/v1/admin/imports` — A — list jobs + status.
- `GET  /api/v1/admin/imports/{job_id}` — A — job detail, progress, errors, summary counts.
- `POST /api/v1/admin/imports/{job_id}/cancel` — A.

### Review & correction
- `GET  /api/v1/admin/versions/{version_id}/sessions?filter=issues&conf=low&page=&limit=` — A
  Staging sessions with confidence, evidence and validation issues.
- `PATCH /api/v1/admin/sessions/{session_id}` — A
  Body: changed fields + `reason`. Writes `session_field_evidence`/audit; sets `extraction_method=manual`.
- `GET  /api/v1/admin/versions/{version_id}/issues` — A
- `POST /api/v1/admin/issues/{issue_id}/resolve` — A
- `GET  /api/v1/admin/versions/{version_id}/source/{page}.png` — A
  Rendered page image (signed URL or proxied) for evidence.

### Diff & publish
- `GET  /api/v1/admin/versions/{version_id}/diff` — A
  `{ added: [...], removed: [...], changed: [{ key, fields: {field: {from,to}} }] }`
- `POST /api/v1/admin/versions/{version_id}/publish` — A (owner)
  Atomic; blocked if blocking issues remain. Returns `publication_record`.
  409 if another version is being published concurrently.
- `POST /api/v1/admin/versions/{version_id}/rollback` — A (owner)
  Re-publishes the previous version; records a rollback publication.

### History & audit
- `GET /api/v1/admin/history` — A — publication records.
- `GET /api/v1/admin/audit?entity=&actor=&from=&to=` — A.

## 8.3 Contract rules

- **Idempotency**: `POST imports` returns the existing `version_id` if the hash matches; `publish`
  on an already-active version is a no-op `200`.
- **Errors**: RFC 7807 `application/problem+json` with `type`, `title`, `status`, `detail`.
- **Pagination**: `?page=&limit=` (max 200) with `X-Total-Count`.
- **Caching (public)**: `Cache-Control: public, max-age=300, stale-while-revalidate=3600`;
  ETag based on version id. No personal data.
- **Rate limiting**: public read 60 req/min/IP; admin login 5 attempts/5 min/IP; uploads 10/hour/user.
- **Auth**: session cookie `HttpOnly; Secure; SameSite=Lax` + CSRF token header for mutations; or
  bearer JWT for future integrations.

## 8.4 Authorisation matrix

| Action | anonymous | reviewer | owner |
|---|---|---|---|
| Read published timetable | ✅ | ✅ | ✅ |
| Upload / run import | ❌ | ✅ | ✅ |
| Correct sessions / resolve issues | ❌ | ✅ | ✅ |
| Publish / rollback | ❌ | ❌ | ✅ |
| View audit log | ❌ | ✅ | ✅ |
| Manage admin users | ❌ | ❌ | ✅ |
