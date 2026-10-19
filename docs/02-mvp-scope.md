# 3. MVP Scope

Scope is anchored to what the discovery (artifact 1) actually shows: one semester PDF, one grid per
cohort, clean text layer, shared classes, continuation pages.

## 3.1 Must-have (MVP, release-blocking)

1. Student: programme → cohort selection for the active period.
2. Student: Today + Weekly views (mobile-first), day switcher.
3. Student: session detail (course name, code, lecturer(s), venue) — showing "not provided" where absent.
4. Student: version label + "last updated".
5. Student: remembered selection; graceful empty/`-x-`/`---` handling.
6. Admin: authenticated upload of a PDF as a new **version**.
7. Admin: automated extraction → normalised staging records with confidence + validation issues.
8. Admin: review UI showing each entry alongside its **source page image**; edit/correct.
9. Admin: duplicate/conflict detection aware of **shared cohorts**.
10. Admin: version diff (add/remove/change) before publish.
11. Admin: **atomic** publish with rollback; previous versions preserved.
12. Admin: import history + audit log.
13. Security: restricted admin access, upload type/size validation, safe PDF handling.
14. Traceability: every published session stores source document + page + extraction method.

## 3.2 Should-have (MVP if the PoC and timeline allow)

- Full-text search within a cohort timetable.
- Course/lecturer/venue index pages.
- Rate limiting + basic monitoring dashboards.
- Calendar `.ics` export per cohort (read-only).

## 3.3 Later

- Notifications (e.g. "your class moved rooms").
- Multiple academic periods / semesters in the UI.
- Multi-institution support.
- Lecturer self-service corrections (with approval).
- Offline/PWA caching.

## 3.4 Explicitly out of scope (for now)

- Student accounts and login.
- Attendance, grades, results, fee systems.
- AI chatbot / natural-language query.
- Full university management system.
- Native mobile applications.
- Fabricating missing course codes, lecturers or venues.

## 3.5 Scope guardrails

- If the PoC shows extraction cannot reliably reach the agreed accuracy, **shrink the MVP** to
  "admin-reviewed import with mandatory manual confirmation of low-confidence cells" rather than
  automating risky inference.
- No feature is added that depends on data the PDF does not contain unless an admin workflow
  supplies it.
