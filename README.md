# Kairos — website

The website for **Kairos**, the DIT teaching timetable. Students pick their class and see
today's and this week's classes, with no login needed. Class reps mark classes live, move
them and post venue heads-ups. Admins import, review and publish timetable versions.

- **Stack:** Next.js 15 (App Router) · React 19 · Tailwind CSS 4 · shadcn/ui
- **API:** separate repo, `kairos-backend` (FastAPI + Postgres)

## How it talks to the API

- The browser only calls this site. `/api/*` is forwarded to the API by
  `app/api/[...path]/route.ts`, so login cookies stay first-party and no CORS is needed.
- Server-rendered pages fetch the API directly (`lib/server-api.ts`).
- Both read their settings **at request time**, so changing them needs a restart, not a
  rebuild:

| Variable | Used by | Default |
|---|---|---|
| `TT_BACKEND_ORIGIN` | `/api/*` proxy | `TT_API_BASE`, then `http://127.0.0.1:8000` |
| `TT_API_BASE` | server-rendered pages | `http://127.0.0.1:8000` |
| `TT_ALLOW_DRAFT_PREVIEW` | preview unpublished versions (dev/staging only) | `false` |

All times are East Africa Time (`lib/time.ts`), whatever the server's or visitor's clock says.

## Run locally

Start the API from `kairos-backend` on port 8000, then:

```bash
npm install
npm run dev          # http://localhost:3000
```

`npm run build` then `npm start` runs the production build on `0.0.0.0:8000`.

## Deploy on deploy.tz

Create a **Deploy New App** with these settings:

| Field | Value |
|---|---|
| Name | `kairos`, which serves `https://kairos.deploy.tz` |
| Stack | Node (18.18 or newer) |
| Repository | this repo; pushes to `main` or `master` auto-deploy |

Environment:

```
TT_BACKEND_ORIGIN=https://kairos-api.deploy.tz
TT_API_BASE=https://kairos-api.deploy.tz
NODE_ENV=production
```

deploy.tz builds the Node stack with `npm install` → `npm run build` → `npm start`. The
`start` script listens on `0.0.0.0:8000`.

Deploy the API first (see `docs/17-deployment.md` in `kairos-backend`) and check that
`https://kairos-api.deploy.tz/healthz` responds.

## Layout

| Path | What |
|---|---|
| `app/` | Routes: `/` home, `/c/[cohort]` class timetable, `/cr` class reps, `/admin` console, `/api/*` proxy |
| `components/` | `timetable/` (day/week views), `cr/` (class-rep controls), `student/`, `admin/`, `ui/` (shadcn) |
| `lib/` | API clients, types, campus-time helpers |
| `public/` | Icons and the offline service worker |
