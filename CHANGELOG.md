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
- Static consistency tests for the JavaScript modules (imports, element ids).
