# CLAUDE.md — TRAKKO

## Project overview

TRAKKO is a mobile-first Progressive Web App (PWA) written in Python to track daily events.

The user defines **Tracks** (e.g. "Menstrual Cycle", "Workout"). Each Track has its own **Event Types** (e.g. "Cycle Start", "Ovulation", "Cycle End" / "Running", "Gym", "Functional Training", "Swimming"). On any day the user logs **Entries** (an occurrence of an Event Type) on a calendar, optionally with a short text note.

Core principle: **extremely simple UI, designed for a phone first.** When in doubt, remove UI rather than add it.

## Language rules

- The whole app (UI labels, messages, API errors, validation messages) is in **English**.
- Code, comments, commit messages, docs and this file are in English.

## Domain model

- **Track**: `id`, `name`, `position` (order), `is_default` (exactly one default).
- **EventType** (belongs to a Track): `id`, `track_id`, `name`, `color` (hex), `icon_kind` (`none` | `emoji` | `text`), `icon_value` (a symbol, a letter or a number; empty when `none`), `position`.
- **Entry** (belongs to an EventType): `id`, `event_type_id`, `date` (ISO date, no time zone), `note` (optional, max 280 chars), `created_at`, `updated_at`.

Rules:
- Multiple entries on the same day are allowed (also of the same Event Type).
- Deleting a Track deletes its Event Types and Entries (ask for confirmation in the UI).
- Deleting an Event Type deletes its Entries (ask for confirmation, show the count).
- Dates are plain calendar dates; never convert them with time zones.

## Tech stack

- Python 3.12, **FastAPI** + **Uvicorn**
- **SQLite** via **SQLAlchemy 2.x** (sync is fine), migrations with **Alembic**
- Pydantic v2 for schemas/validation
- Frontend: server-rendered shell with **Jinja2** + **vanilla JavaScript (ES modules)** and plain CSS. **No Node build step, no frontend framework** unless explicitly requested.
- Tests: **pytest**, **httpx** TestClient; lint/format: **ruff**
- Dependencies in `requirements.txt` (runtime) and `requirements-dev.txt` (dev)

Do not add heavy dependencies without asking first.

## Project structure

```
trakko/
├── CLAUDE.md
├── README.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── LICENSE
├── Dockerfile
├── .dockerignore
├── .gitignore
├── .env.example
├── requirements.txt
├── requirements-dev.txt
├── alembic.ini
├── alembic/
├── app/
│   ├── main.py            # FastAPI app, routes registration, PWA routes
│   ├── config.py          # settings from environment variables
│   ├── db.py              # engine, session
│   ├── models.py          # SQLAlchemy models
│   ├── schemas.py         # Pydantic schemas
│   ├── routers/           # tracks.py, event_types.py, entries.py, stats.py
│   ├── services/          # business logic (stats, calendar queries)
│   ├── templates/         # base.html, index.html, ...
│   └── static/
│       ├── manifest.webmanifest
│       ├── service-worker.js   # served from "/" scope via a dedicated route
│       ├── icons/              # 192, 512, maskable, apple-touch-icon
│       ├── css/
│       └── js/                 # ES modules: api.js, calendar.js, swipe.js, ...
├── tests/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── USER_GUIDE.md
│   ├── DEPLOYMENT.md
│   └── DEVELOPMENT.md
└── .github/workflows/
    ├── ci.yml              # lint + tests
    └── docker.yml          # build & push image to GHCR
```

## UI / UX specification

Mobile-first (design for 360–430 px wide), usable on desktop as a centered column. Touch targets at least 44 px. Support light and dark mode via `prefers-color-scheme`.

### Home screen (3 zones)

1. **Top – Track selector.** Shows the current Track name. Swipe left/right (and visible arrow buttons) to switch Track. Starts on the default Track. Show dots or "2/5" to indicate position.
2. **Center – Calendar.** Three views, switchable with a small segmented control: **Day**, **Week**, **Month** (default: Month).
   - Swipe left/right moves to the next/previous period in the current view.
   - Days show small colored markers/icons of the entries of the *current Track* only.
   - Highlight today. A "Today" button returns to the current date.
3. **Bottom – Navigation bar.** Two items: **Settings** and **Statistics** (plus Home).

### Day interaction

- Tapping a day (in Day, Week or Month view) opens the **day editor** (bottom sheet / full-screen modal on mobile).
- The editor lists the day's entries for the current Track, and allows to: **add** an entry (choose Event Type, optional note), **edit** an entry (change type/note), **delete** an entry.
- Adding an entry must take at most **2 taps + optional note** (tap day → tap event type → Save).

### Settings

- Manage Tracks: create, rename, reorder, set default, delete.
- Manage Event Types per Track: name, color (preset palette + custom), icon (none / emoji / single letter / number), reorder, delete.
- Data: export all data as JSON, import JSON.

### Statistics

Per Track and selectable period (month / year / all):
- Count per Event Type
- Entries per week/month (simple bar chart)
- Streaks and days since last entry for each Event Type
- Average interval between consecutive entries of an Event Type (useful for the cycle example)
- Heatmap of activity

Charts: draw with inline SVG or `<canvas>` in plain JS. Do not add a chart library without asking.

## PWA requirements

- `manifest.webmanifest`: name "TRAKKO", `display: standalone`, `start_url: /`, theme/background colors, icons 192/512 + maskable.
- Service worker: precache the app shell (HTML, CSS, JS, icons); network-first for `/api/*` with graceful failure; show a clear offline banner. Version the cache name and clean old caches on activate.
- The service worker must be served from `/service-worker.js` (root scope) with correct headers.
- iOS support: `apple-touch-icon`, `apple-mobile-web-app-capable` meta tags, safe-area insets.
- Must pass Lighthouse PWA checks. HTTPS is required in production (`localhost` is exempt).
- v1 is online-first with offline shell. Offline writes (queue + sync) are a **future enhancement**, not part of v1.

## API conventions

- REST JSON under `/api/v1`. OpenAPI docs auto-generated at `/docs`.
- Resources: `/tracks`, `/tracks/{id}/event-types`, `/entries` (filter by `track_id`, `from`, `to`), `/stats`, `/export`, `/import`.
- Use proper HTTP status codes; errors as `{ "detail": "..." }` in English.
- Validate everything with Pydantic (hex colors, date format, note length, icon rules).

## Authentication & data

- v1 is **single-user**. Protect the app with a simple shared secret (`TRAKKO_PASSWORD` env var → session cookie) when exposed publicly; if unset, run without auth for local use.
- Never hard-code secrets. Configuration only through environment variables (`TRAKKO_DB_PATH`, `TRAKKO_PASSWORD`, `TRAKKO_SECRET_KEY`).
- Never commit `.env`, database files or backups. Provide `.env.example`.
- SQLite file lives in a configurable path (a mounted volume in containers).

## Coding conventions

- Type hints everywhere; keep functions small; business logic in `services/`, not in routers.
- Format and lint with `ruff` (`ruff format`, `ruff check`).
- Vanilla JS: ES modules, no globals, no inline scripts; accessible markup (labels, aria attributes, keyboard support).
- Add or update tests for every behavior change. Target: API and services well covered.

## Commands

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head                       # create/upgrade the DB
uvicorn app.main:app --reload              # run at http://localhost:8000
pytest                                     # run tests
ruff format . && ruff check .              # format + lint
```

## Container & GitHub

**Docker is NOT installed on the developer's Mac. Never run `docker` commands locally.** The image is built only by GitHub Actions.

- `Dockerfile`: `python:3.12-slim`, non-root user, installs `requirements.txt`, runs `alembic upgrade head` then Uvicorn on port 8000, `VOLUME` for the SQLite data directory, `HEALTHCHECK` on `/health`.
- `.dockerignore`: `.venv`, `.git`, `__pycache__`, `.env`, `tests`, `docs`.
- `.github/workflows/ci.yml`: on pull request and push → set up Python, install deps, `ruff check`, `pytest`.
- `.github/workflows/docker.yml`: on push to `main` and tags `v*` → build with Buildx and push to **GHCR** (`ghcr.io/<owner>/trakko`) using `GITHUB_TOKEN`, with metadata tags (`main`, `sha`, semver).
- Expose a `/health` endpoint returning `{"status": "ok"}`.

## Documentation (must be generated and kept up to date)

Documentation is a deliverable, not an afterthought. Create and maintain, in English:

- `README.md`: what TRAKKO is, features, screenshots placeholder, quick start (local), configuration table (env vars), run with the GHCR image, badges (CI, Docker), license.
- `docs/ARCHITECTURE.md`: components, data model diagram (Mermaid ER), request flow, PWA/service worker strategy, key design decisions.
- `docs/API.md`: endpoint overview with examples (details live in the OpenAPI at `/docs`).
- `docs/USER_GUIDE.md`: how to install the PWA on iOS/Android, create Tracks and Event Types, log/edit/delete entries, use views and swipes, read statistics, export/import.
- `docs/DEPLOYMENT.md`: running the container from GHCR, volume for the DB, env vars, HTTPS/reverse proxy notes.
- `docs/DEVELOPMENT.md` and `CONTRIBUTING.md`: setup, commands, tests, branch/PR conventions, commit style.
- A `CHANGELOG.md` (Keep a Changelog format).

Whenever you change behavior, API or configuration, update the relevant docs in the same change.

## Git workflow

- Work on feature branches; `main` is always deployable.
- Small, focused commits with imperative messages (e.g. "Add entry editor bottom sheet").
- Do not commit generated or local files (`.venv`, `*.db`, `.env`).
- Only commit or push when asked.

## Working agreement for Claude

1. For any non-trivial feature, propose a short plan first and wait for approval.
2. Build in this order: project skeleton → data model + migrations → API + tests → UI shell and PWA → calendar views → day editor → settings → statistics → docs → CI/Docker workflows.
3. Run `pytest` and `ruff` before declaring a task done.
4. Keep the UI minimal. Do not add features not described here without asking.
5. Ask before adding dependencies, changing the stack, or deviating from this document.

## Out of scope for v1

Multi-user accounts, push notifications, offline write sync, cloud sync, i18n (English only), native apps.