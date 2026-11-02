# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Project skeleton: FastAPI app, `/health` endpoint, environment-based configuration,
  tooling (ruff, pytest) and initial tests.
- Data model (`Track`, `EventType`, `Entry`) with SQLAlchemy 2.x, cascade deletes,
  a single-default-Track constraint and Alembic migrations. The initial migration
  seeds one default Track named "My Track".
- REST API under `/api/v1`: Tracks, Event Types (with entry counts and reordering), Entries
  (filter by Track, Event Type and date range), statistics (counts, weekly/monthly buckets,
  streaks, days since last, average interval, heatmap), JSON export and import.
- Optional shared-password authentication with a signed, HTTP-only session cookie
  (`TRAKKO_PASSWORD` + `TRAKKO_SECRET_KEY`).
- API documentation in `docs/API.md`.
- UI shell: Jinja2 page with the Track selector (arrows, swipe, "n/m" indicator), Home /
  Statistics / Settings navigation bar, sign-in form and an offline banner, in plain CSS
  (light/dark, safe-area insets) and vanilla ES modules.
- PWA: web app manifest, generated icons (192, 512, maskable, apple-touch-icon), iOS meta tags,
  and a service worker served from `/service-worker.js` that precaches the app shell with a
  content-hashed cache name and uses network-first for `/api/*` (read-only copies of GET
  responses are used when offline).
- `jinja2` runtime dependency.
- Calendar on the home screen with Day, Week and Month views (default Month, Monday first),
  swipe/arrow navigation, "Today" button, today highlight and per-Track entry markers (icon or
  color dot, "+n" when a month cell has more than three). Tapping a day dispatches a
  `trakko:day-tap` event for the day editor.
- Day editor: bottom sheet (native `<dialog>`) opened by tapping a day in any view. It lists the
  day's entries for the current Track and adds, edits (type, note) and deletes entries; Save and
  Delete close the sheet and refresh the calendar.
- Settings screens (`#/settings`, `#/settings/tracks/<id>`): manage Tracks and Event Types with
  reordering, default Track, color palette plus custom color, icon picker with live preview,
  confirmation dialogs that show what will be deleted, JSON export/import and sign out.
- Statistics screen with month/year/all periods, per Event Type cards (count, streaks, days since
  last entry, average interval), an SVG bar chart and an SVG activity heatmap.
- `today` query parameter for `GET /stats`, so a past period can be shown while streaks and
  "days since last" keep using the current day.
- Static consistency tests for the JavaScript modules (imports, element ids, editor, settings and
  statistics markup, service worker cache rules).

- Documentation: `docs/ARCHITECTURE.md` (components, data model, request flow, service worker),
  `docs/USER_GUIDE.md`, `docs/DEPLOYMENT.md`, `docs/DEVELOPMENT.md`, `CONTRIBUTING.md`, and a
  complete README (badges, features, container usage, configuration, documentation index).
- Tests that keep the documentation consistent with the code (links, settings, endpoints, files).
- Container image: `Dockerfile` (`python:3.12-slim`, non-root user, `/data` volume, migrations on
  start, health check) and `.dockerignore`.
- GitHub Actions: `ci.yml` (format check, lint, tests) and `docker.yml` (build, smoke test and push
  of `linux/amd64` and `linux/arm64` images to GHCR on `main` and `v*` tags).
- Tests for the Dockerfile, `.dockerignore` and workflows, and a check that every runtime import is
  listed in `requirements.txt`.

### Changed
- API validation messages no longer start with pydantic's "Value error, " prefix.
- The service worker no longer stores copies of `/api/v1/export`; signing out also clears the
  cached API responses.
