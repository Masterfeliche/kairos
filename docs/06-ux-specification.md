# 7. UX Specification

Two distinct interfaces: the **student site** (public, fast, mobile-first) and the **admin console**
(authenticated, dense, task-oriented). They share design tokens, not layouts.

## 7.1 Design principles

- Clarity over decoration; accuracy is the product.
- Mobile-first; readable at 360 px without horizontal scrolling.
- Show uncertainty and "not provided" honestly.
- Always show *which version* of the timetable the user is looking at.

## 7.2 Student information architecture

```
/                       Home: pick programme → cohort, or resume last
/p/[programme]          Cohort list for a programme
/c/[cohort]             Timetable (Today default)
/c/[cohort]?view=week   Weekly view
/c/[cohort]/course/[id] Session detail (optional deep link)
/about                  What this is, data source, last update
```

## 7.3 Student key screens

### Screen S1 — Home / selection
- Big, tap-friendly programme list grouped by level (BEng, Diploma, BTech, Masters).
- Under a programme, cohort chips (`BENG24CE-1`…).
- If a cohort was previously chosen, a **"Continue: BENG24CE-1"** card at top.
- Version banner: *"Semester I • updated 10 Mar 2026"*.

### Screen S2 — Today (default after selection)
- Header: cohort code, day name + date, version + last-updated.
- **Agenda list** (chronological), the recommended mobile layout:
  - Time range (bold), course title, code, lecturer, venue.
  - A subtle separator line = now; past classes dimmed.
  - Free gaps shown as thin "Free 12:00–13:00" rows.
- Empty state: "No classes today" with a link to the week.
- Switcher: `◀ Prev · [Mon Tue Wed Thu Fri] · Next ▶`.

### Screen S3 — Weekly view
- **Agenda-by-day** on mobile: five collapsible day sections (today expanded), each an agenda list.
- **Grid** on wide screens (≥ 768 px): Mon–Fri columns × time rows, cards instead of dense text.
- Recommendation from discovery: because a raw 5×14 text grid is unreadable on phones, use
  **agenda-first with an optional grid on desktop**. Never shrink the source grid onto a phone.

### Screen S4 — Session detail
- Course name, code, department.
- Day, start–end, duration.
- Lecturer(s).
- Venue (room code + human name if known).
- `Shared with: OD26ERE-1` when applicable.
- Source footnote: "From [document name], page N".

### Screen S5 — Empty / error / offline
- `-x-` periods: "Not scheduled".
- `---`: omitted from the timeline (shown only as gaps).
- Load error: retry + "showing last saved data" if cached.

## 7.4 Admin console

```
/admin                  Dashboard: active version, pending imports, issues
/admin/imports          List + status of import jobs
/admin/imports/new      Upload PDF, confirm period + version label
/admin/imports/[id]     Review: summary, warnings, tables of sessions
/admin/imports/[id]/review   Per-session review with source-page image side panel
/admin/versions/[id]/diff    Compare draft vs active (added/removed/changed)
/admin/publish          Confirm + publish (owner only)
/admin/history          Publication history + rollback
/admin/audit            Audit log
```

### Screen A1 — Review (most important)
- Split view: **left** = editable session table (filter: low-confidence, missing code, overlaps);
  **right** = rendered source page image with the cell highlighted (from `source_cell_bbox`).
- Each row shows confidence badges and per-field evidence reasons.
- Inline edit; every change requires a reason and is audit-logged.
- "Accept all high-confidence" + "Show only issues" toggles; low-confidence must be explicitly
  resolved before publish is enabled.

### Screen A2 — Version diff
- Three groups: **Added**, **Removed**, **Changed** (field-level before/after).
- Changed rows are individually approvable; unresolved `error`-severity issues block publishing.

### Screen A3 — Publish
- Shows the diff summary, blocking-issue count, and target period.
- Explicit confirmation; result is atomic; offers "view live" and "rollback to previous".

## 7.5 Accessibility & performance

- WCAG 2.1 AA contrast; visible focus rings; full keyboard operation; semantic headings/labels.
- `prefers-reduced-motion` respected.
- Server-render the student pages; ship minimal JS; lazy-load the week view.
- Data payloads are small (a cohort has ~10–40 sessions).
- Works on slow connections; target < 2.5 s first view on 3G.

## 7.6 Design tokens (shared)

- Neutral background, single accent colour for actions, colour-blind-safe status badges
  (info/success/warn/error).
- Type scale optimised for readability on small screens; generous tap targets (≥ 44 px).
