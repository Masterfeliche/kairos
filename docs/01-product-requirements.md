# 2. Problem Statement & Product Requirements

## 2.1 Problem statement

DIT publishes teaching timetables as a large PDF (160 pages, one grid per class). Students must
open the file, find their cohort's page, and read a dense grid across 14 hourly rows. This is slow
on desktop and painful on a phone, and it breaks whenever DIT republishes the file. There is no
structured, searchable, always-current representation of the timetable.

**Goal:** give every DIT student a fast, mobile-first way to find their correct timetable, and give
authorised staff a safe, traceable way to publish revised timetables without developer involvement.

## 2.2 Stakeholders

| Type | Stakeholder | Interest |
|---|---|---|
| Primary | Students (all programmes/cohorts) | Find "my classes today / this week" quickly and correctly |
| Primary | Timetable/Timetabling Office staff (administrator) | Import, verify, correct and publish versions safely |
| Secondary | Lecturers | Correct venues/times (read-only initially; corrections via admin) |
| Secondary | Registrar / Academic Office | Authoritative publication, audit trail |
| Secondary | IT Operations | Simple, low-cost, maintainable, secure deployment |
| Secondary | Developers/maintainers | Maintainable, testable, clearly bounded codebase |
| Out of scope initially | Parents, alumni, external institutions | Future expansion only |

## 2.3 Personas & journeys

### Student — "Find today's classes"
1. Opens the site (mobile).
2. Picks academic period (defaults to the active one).
3. Picks programme → cohort (e.g. *BEng Civil Engineering → BENG24CE-1*).
4. Sees **Today** (default day) with chronological course cards.
5. Switches to another day or **Week**.
6. Taps a course to see code, lecturer, venue.
7. Sees gaps between classes ("free 12:00–13:00").
8. Returns later — the last selection is remembered.
9. Always sees a **"Last updated"** indicator and version label.

### Administrator — "Publish a revision"
1. Signs in (restricted access).
2. Uploads the new official PDF.
3. Confirms academic period + version label.
4. Runs the import (background job).
5. Reviews extraction results, warnings and low-confidence entries.
6. Opens any uncertain entry next to its **source PDF page image**.
7. Corrects records, resolves validation issues.
8. Compares the draft with the currently published version (adds/removes/changes).
9. Approves → atomic publication.
10. Reviews import history, statuses and errors; can roll back safely.

### Non-functional requirements

| Area | Requirement |
|---|---|
| Performance | First contentful view < 2.5 s on a 3G-class connection; search/selection < 300 ms |
| Mobile-first | Works on 360 px-wide low-end phones; no horizontal scrolling of the grid |
| Availability | 99% monthly (MVP); graceful read-only mode if admin services are down |
| Security | Admin actions authenticated + authorised; uploads validated; audit logged |
| Traceability | Every published session links to source document + page; changes audited |
| Data integrity | A failed import never corrupts or replaces the published timetable |
| Accessibility | WCAG 2.1 AA: contrast, keyboard nav, semantic labels |
| Maintainability | Single-language backend + typed frontend; automated tests; CI |
| Cost | Runs on a single small VM / managed Postgres within a small budget |

## 2.4 Functional requirements (prioritised)

Legend: **M** must (MVP) · **S** should (MVP if time) · **L** later · **X** out of scope.

| ID | Requirement | Pri |
|----|-------------|-----|
| FR-01 | Browse programmes and cohorts for the active period | M |
| FR-02 | Show a **Today** view per cohort (chronological, with free gaps) | M |
| FR-03 | Show a **Weekly** view per cohort | M |
| FR-04 | Day switcher (Mon–Fri) and quick "next/previous day" | M |
| FR-05 | Course/lecturer/venue detail per session | M |
| FR-06 | Display version label + last-updated timestamp | M |
| FR-07 | Remember last cohort selection locally | M |
| FR-08 | Responsive mobile-first layout | M |
| FR-09 | Search within a cohort's timetable (course/lecturer/venue) | S |
| FR-10 | Show shared/combined cohorts on a session | S |
| FR-11 | Admin upload + import of PDF | M |
| FR-12 | Automated extraction + normalisation + validation warnings | M |
| FR-13 | Admin review with source-page evidence + corrections | M |
| FR-14 | Version compare (added/removed/changed) before publish | M |
| FR-15 | Atomic publish + preserve previous versions | M |
| FR-16 | Import history, statuses, error reporting | M |
| FR-17 | Duplicate + conflict detection with shared-class awareness | M |
| FR-18 | Audit log of admin actions | M |
| FR-19 | Rate limiting on public + admin endpoints | S |
| FR-20 | Notifications / calendar export (.ics) | L |
| FR-21 | Additional institutions / multi-tenant | L |
| FR-22 | Student accounts, attendance, grades, AI chatbot | X |

## 2.5 Constraints & assumptions

- The PDF is the authoritative source; the app must never fabricate values.
- Uncertainty must be visible to admins and never silently published as verified.
- First release = responsive website; no native app.
- Staffing is small; favour a monolithic, well-tested app over microservices.
- Verification date: the source file footer says generated 2026-03-10; treat the whole file as one
  version unless DIT confirms otherwise. **[OPEN]**
