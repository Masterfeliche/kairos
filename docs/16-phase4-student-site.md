# 17. Phase 4 - Student website

Status: **core implemented + CR role (live/reschedule/institute), shadcn/ui adopted; dark-by-default theme + landing page**. Phase 4 DoD accessibility/performance certification **passed** (see §17.6).

## 17.1 Goal

A public, mobile-first, read-only site where a student picks their programme/class and sees their
timetable (Today by default, plus a Week view) - with no login. Students have no accounts
(`docs/08-security-operations.md` §9.1).

## 17.2 Routes (Next.js App Router, server-rendered)

| Route | File | Screen |
|---|---|---|
| `/` | `app/page.tsx` | **S1** selection: version banner, "Continue" card, programme list grouped by level, search |
| `/c/[cohort]` | `app/c/[cohort]/page.tsx` | **S2** Today (default); **S3** Week — aligned 30-min time grid on `md+`, collapsible agenda on mobile |
| `/c/[cohort]` (session `<details>`) | `components/timetable/SessionCard.tsx` | **S4** session detail (live status, reschedule, source; optional CR action slot) |
| `/about` | `app/about/page.tsx` | data source + last update |
| `/cr/login` | `app/cr/login/page.tsx` | CR sign-in (role `cr`) |
| `/cr` | `app/cr/page.tsx` | CR: **same Day/Week timetable as students** (`components/timetable/TimetableView.tsx`) with a per-session control slot (live status, reschedule, venue heads-up) + notices panel |
| `/cr/institute` | `app/cr/institute/page.tsx` | Institute timetable + room availability (notices included) |
| (404) | `app/not-found.tsx` | **S5** empty/error |

Components (shadcn/ui): `SiteHeader`, `VersionBanner`, `VenueNoticeBanner`, `ContinueCard`, `ProgrammePicker`; shared timetable `TimetableView` + `SessionCard` (Day/Week) used by both students and CRs; CR pages use Card/Button/Dialog/Select/Table etc.

### Venue heads-up ("occupied soon")

A CR can mark a venue as about to be occupied (`venue_notice` table). People see it on the class page
(`VenueNoticeBanner`) so they know **when to leave** a venue, and CRs see it in the room-availability
result (`free=false` while the notice window overlaps) so a venue is **not taken by mistake**.
Endpoints: CR `POST/GET/DELETE /api/v1/cr/venue-notices`; public `GET /api/v1/venue-notices`.

## 17.3 Data & rendering

- Server components fetch the backend directly via `lib/server-api.ts`
  (`TT_API_BASE`, default `http://127.0.0.1:8000`) with `cache: 'no-store'` → SSR HTML, minimal JS.
- Navigation uses links (`?day=`, `?view=`) so it works without JS and is keyboard-accessible.
- "Now": sessions already ended are dimmed on today; gaps render as thin "Free HH:MM-HH:MM" rows.
- Missing values are shown honestly ("Not provided"), never guessed.

## 17.4 Public API (added/extended)

- `GET /api/v1/programmes` - programmes with their cohorts (for S1 grouping).
- `GET /api/v1/versions/active` - active published version + banner metadata
  (`label`, `updated_at`, `source_filename`, `is_preview`).
- `GET /api/v1/timetable?cohort_code=...` - `{ cohort, version, sessions[] }`; each session carries
  code, name, department, lecturers, venue, `shared_with`, `source_page`.

### Draft preview (dev/staging only)

`TT_ALLOW_DRAFT_PREVIEW=true` lets the public endpoints fall back to the latest `review` version
when nothing is published, so the student site can be exercised before the publish gate is cleared
(GET `.../versions/active?preview=1`, `.../timetable?cohort_code=..&preview=1`). The UI shows a
"Preview - not published" badge. **Must stay off in production.**

## 17.5 Verification done

- `npm run build` passes; routes `ƒ /`, `ƒ /about`, `ƒ /c/[cohort]` render server-side.
- Rendered `OD24COE-1`: 11 sessions, source filename correct, preview badge present.
- Home lists programmes grouped by level and finds `OD24COE-1`; unknown cohort → 404.

## 17.6 Accessibility & performance certification (Phase 4 DoD) - PASSED

Certified against the **production build** (`next build` + `next start` on :3000, dark theme,
mobile emulation) with Lighthouse 12 (mobile preset) and axe-core 4 via headless Chrome.

Lighthouse (mobile, all categories):

| Page | Performance | Accessibility | Best practices | SEO |
|---|---|---|---|---|
| `/` (landing) | 94 | 100 | 96 | 100 |
| `/c/OD24COE-1` (cohort) | 96 | 100 | 96 | 100 |

axe-core (WCAG 2.0/2.1 A + AA rules) - all categories zero:

| Page | critical | serious | moderate |
|---|---|---|---|
| `/`, `/c/OD24COE-1` (day + week), `/cr/login`, `/about` | 0 | 0 | 0 |

DoD met: Lighthouse performance ≥ 90 and axe = 0 critical on `/` and `/c/[cohort]`.

Fix applied during certification: `SessionCard` dimmed ended/not-held sessions with
`opacity-55`, which blended `text-muted-foreground` to ~2.9:1 contrast and failed WCAG AA.
Replaced whole-card opacity with a `bg-muted/40` tint so text keeps full contrast while the
card still reads as de-emphasised.

## 17.6b Design pass - de-slop (killaislop.com tells)

Following the field guide at killaislop.com, the landing/about/404 visuals were cleaned of the
"AI slop" tells we had hit (brand accent and layout kept). Changes:

- **Gradient headline text** (`bg-clip-text`) removed - the h1 is now a solid `text-foreground`.
- **Oversized full-sentence headline** compressed: "Your class timetable, always in your pocket"
  is now the 3-word h1 "Your class timetable" with the rest in the subline.
- **Tinted rounded icon tiles** (`bg-primary/10 text-primary` squares) dropped from the feature
  grid, the about page and the 404 icon; icons are now bare `size-5 text-primary`.
- **Atmosphere gradients** removed: the hero's radial glow halo and the `.muted-grid` stripe
  pattern (and the `.muted-grid` class) are gone; the phone mockup's `bg-primary/20 blur-3xl`
  halo and colored `shadow-primary/10` were flattened.
- **Springy hover lift** (`hover:-translate-y-0.5`) removed from feature cards.

Re-certified after the pass: Lighthouse `/` = 94 / 100 / 96 / 100, axe = 0 critical.

## 17.7 Remaining (non-blocking)

- 360 px visual pass + `prefers-reduced-motion`; verify current-time separator/dimming across timezones.
- Consider a wide-screen positioned time-grid (S3 currently uses per-day columns).
- Cache/ISR for the active version; `stale-while-revalidate` to hit the 3G target.
