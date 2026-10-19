# 18. Deployment: deploy.tz + Postgres in Docker

```
 students / class reps / admins
            │ HTTPS
            ▼
 ┌──────────────────────────────┐      server-side + /api proxy      ┌──────────────────────────────┐
 │ deploy.tz app "kairos"       │ ─────────────────────────────────▶ │ deploy.tz app                 │
 │ APP_ROLE=web · Node stack     │                                    │ "kairos-api"                  │
 │ Next.js (next start :8000)    │                                    │ APP_ROLE=api · Python stack   │
 └──────────────────────────────┘                                    │ FastAPI (uvicorn :8000)       │
                                                                      └──────────────┬───────────────┘
                                                                                     │ TT_DATABASE_URL
                                                                                     ▼
                                                                      ┌──────────────────────────────┐
                                                                      │ Your server: Docker           │
                                                                      │ postgres:16 (deploy/postgres) │
                                                                      └──────────────────────────────┘
```

deploy.tz builds each app from the GitHub repository into a Docker image. On the
**Node stack** it generates the build itself:

```
COPY package.json, package-lock.json → npm install → COPY . . → npm run build → npm start
```

The `Shipfile` is used on the other stacks. This repository is deployed as **two** apps,
and every entry point leads to the same two scripts, `deploy/setup.sh` and
`deploy/start.sh`:

- the root `package.json` (`npm run build` / `npm start`)
- the root `requirements.txt`
- the `Shipfile`

Each app's role comes from `APP_ROLE`. When that is not set, for example during the
Docker build, the role is inferred: a run started by npm is the website, and an image
with Python and no Node is the API.

The scripts never need runtime-only settings while the image is being built.
`TT_DATABASE_URL` and the backend URL are read when the app starts.

The browser only talks to the website. The website proxies `/api/*` to the API app, so
login cookies stay first-party.

## 1. Run Postgres on your server

```bash
cd deploy/postgres
cp .env.example .env        # set a long random POSTGRES_PASSWORD
docker compose up -d
docker compose ps           # wait for "healthy"
```

- **Reachability.** The deploy.tz API app must be able to reach this host on `POSTGRES_PORT`
  (5432 by default). Open that port in the server firewall **only** for deploy.tz's
  outbound addresses; ask SubCode Africa support for them. Never leave 5432 open to the
  whole internet with a weak password.
- **Encryption.** The stock image speaks plain TCP. If the connection crosses the public
  internet, put Postgres behind TLS: a certificate plus `ssl=on`, then add
  `?sslmode=require` to `TT_DATABASE_URL`. A private network or VPN between the two is
  another option.
- **Backups.** Data lives in the `timetable-pgdata` Docker volume. Back it up nightly:

  ```bash
  docker exec timetable-postgres pg_dump -U timetable -Fc timetable > timetable-$(date +%F).dump
  ```

  Restore with `pg_restore -U timetable -d timetable --clean <file>` inside the container.

## 2. Put the code on GitHub

deploy.tz deploys from GitHub. It auto-deploys on pushes to `main` or `master`. For a
private repository, first connect GitHub under deploy.tz **Settings → configure access**.

## 3. Create the API app

On deploy.tz, choose **Deploy New App**:

| Field | Value |
|---|---|
| Name | `kairos-api` (becomes `kairos-api.deploy.tz`) |
| Stack | Python (3.11 or newer) |
| Repository | this repo |
| Environment | see `deploy/env/api.env.example` |

Required variables:

```
APP_ROLE=api
TT_DATABASE_URL=postgresql://timetable:<password>@<postgres-host>:5432/timetable
TT_FRONTEND_ORIGIN=https://kairos.deploy.tz
TT_SECURE_COOKIES=true
TT_ALLOW_DRAFT_PREVIEW=false
```

The image installs `requirements.txt` at build time. On every start, `deploy/start.sh`
runs **`alembic upgrade head`** before uvicorn. On a fresh database this creates the
schema; after an update it applies new migrations before the new code serves requests. Check `https://kairos-api.deploy.tz/healthz` returns `{"status":"ok"}`.

## 4. Create the website app

| Field | Value |
|---|---|
| Name | `kairos` (the public URL students use, `kairos.deploy.tz`) |
| Stack | Node (18.18 or newer) |
| Repository | the same repo |
| Environment | see `deploy/env/web.env.example` |

```
APP_ROLE=web
TT_BACKEND_ORIGIN=https://kairos-api.deploy.tz
TT_API_BASE=https://kairos-api.deploy.tz
NODE_ENV=production
```

`APP_ROLE=web` is optional here, because npm marks the build as the website. The
backend URL is read when each request comes in: `/api/*` is forwarded by
`frontend/app/api/[...path]/route.ts`. If the API URL changes, update the variable and
restart the website. No rebuild is needed.

## 5. Load the data

Pick one.

**A. Move your existing local data (recommended).** This keeps the review corrections,
accounts and history you already have. From your machine, with the server's Postgres
reachable:

```bash
cd backend
set TT_DATABASE_URL=postgresql://timetable:<password>@<postgres-host>:5432/timetable   # PowerShell: $env:TT_DATABASE_URL="..."
python -m alembic upgrade head                      # skip if the API app already ran it
python -m app.cli copy-db --source sqlite:///./smarttimetable.db
```

`copy-db` refuses to write into a non-empty database. It copies every table parent-first.
A local run moved 32,619 rows in 22 tables. Copy **before** anyone signs in to the new
site, because signing in creates rows and the target is then no longer empty.

**B. Start fresh.**

```bash
python -m app.cli create-admin you@dit.ac.tz --role owner
python -m app.cli import "TEACHING TIMETABLE ... .pdf"
# review + resolve issues in /admin, then publish
```

Run these commands from your machine with `TT_DATABASE_URL` pointing at production.

## 6. Updating

Push to `main` or `master`; both apps redeploy. The API's build step applies migrations
first. Stop the apps and back up the database before deploying a migration that changes
data (see `backend/migrations/versions`).

## Known limits on deploy.tz

- **Uploaded PDFs are stored on local disk** (`TT_STORAGE_DIR`). deploy.tz does not
  document persistent disks, so assume they are lost on redeploy. The timetable data
  itself is safe in Postgres. After a redeploy, though, the admin review screen can no
  longer show the source-page images for an earlier import. Finish reviewing an import
  before redeploying, or re-import the PDF. Storing PDFs in Postgres or object storage
  would fix this.
- **Unverified platform details.** Not documented: the exact Python and Node versions on
  each stack, and whether one Shipfile can serve two stacks. If a build fails, check the
  build logs. The two scripts are plain POSIX `sh` and print a clear error when
  `APP_ROLE` or a required variable is missing.
- **Ports.** Both apps listen on `0.0.0.0:8000`. The `Shipfile` declares `PORT=8000`,
  which deploy.tz detects.
- **Root manifests.** The Node and Python stacks look for `package.json` and
  `requirements.txt` at the repository root, not in `frontend/` or `backend/`. Both
  exist at the root and only hand off to those folders:
  - `package.json` has no dependencies; `npm run build` and `npm start` call the
    deploy scripts.
  - `requirements.txt` installs `./backend`.

  If a build fails with "package.json missing" or "requirements.txt missing", the app
  is building an old commit. Redeploy from the latest `master`.
- **Build exit code 127** ("command not found") meant an older `setup.sh` was looking
  for Python inside the Node image. Current scripts print `kairos setup: APP_ROLE=...`
  first. If a build log doesn't show that line, it is not running the current code.

## Local equivalent (for testing the production setup)

```bash
cd deploy/postgres && POSTGRES_PASSWORD=dev POSTGRES_PORT=55432 docker compose -p tt-local up -d
cd backend
set TT_DATABASE_URL=postgresql://timetable:dev@127.0.0.1:55432/timetable
python -m alembic upgrade head
python -m uvicorn app.main:app --port 8000 --proxy-headers
# run the backend test suite on Postgres (uses a throwaway database):
set TT_TEST_DATABASE_URL=postgresql://timetable:dev@127.0.0.1:55432/timetable_test
python -m pytest
```
