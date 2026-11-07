# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.3] - 2026-11-07

### Fixed
- The selected Track is kept when the page reloads, as iOS does when the installed app is used,
  so Statistics (and Home) no longer jump back to the default Track. Closing the app still starts
  on the default Track.

## [0.1.2] - 2026-11-06

### Fixed
- Statistics no longer show the previous Track's numbers while the selected Track's statistics
  load (noticeable on a slow connection), and a late answer for the previous Track can no longer
  replace them.

## [0.1.1] - 2026-11-03

### Fixed
- **Upgrading a database that already had accounts no longer deletes its data.** Migration `0003`
  rebuilds the `users` table, and SQLite does that by dropping the old one; with foreign keys
  enforced the drop cascaded into every user's Tracks, Event Types and Entries and removed them all.
  Migrations now run with foreign key enforcement off (the connection used by the app still has it
  on) and the result is verified with `PRAGMA foreign_key_check`.
- Tests that migrate real data (several users, Tracks, Event Types and Entries) through every step,
  up and down, so a migration that loses rows can no longer pass.

> **If you upgraded to 0.1.0 (or to a `latest`/`main` image built before 0.1.1) from a database that
> already had accounts, its Tracks, Event Types and Entries were deleted** (the users and their
> passwords were kept). Restore the `trakko.db` copy or the JSON export you made before upgrading.
> Databases created fresh on 0.1.0, or migrated from before accounts existed, were not affected.

## [0.1.0] - 2026-11-03

### Added
- Project skeleton: FastAPI app, `/health` endpoint, environment-based configuration,
  tooling (ruff, pytest) and initial tests.
- Data model (`Track`, `EventType`, `Entry`) with SQLAlchemy 2.x, cascade deletes,
  a single-default-Track constraint and Alembic migrations. The initial migration
  seeds one default Track named "My Track".
- REST API under `/api/v1`: Tracks, Event Types (with entry counts and reordering), Entries
  (filter by Track, Event Type and date range), statistics (counts, weekly/monthly buckets,
  streaks, days since last, average interval, heatmap), JSON export and import.
- Authentication with a signed, HTTP-only session cookie.
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

- README rewritten with a banner, real screenshots, a feature tour and honest notes on limits; the
  images, an SVG banner and a 1280x640 social preview for GitHub live in `docs/assets/`.
- Tests for the README: images exist with the right size and alt text, SVGs are valid and contain no
  scripts, and links and anchors resolve.
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

- **Accounts (multi-user).** Several people can share one installation: register, sign in and sign
  out with a username and password (`POST /api/v1/auth/register`, `login`, `logout`, and `status`
  now reports the signed-in user). Tracks, Event Types, Entries, statistics, export and import are
  per user; other users' resources answer 404. Passwords are stored as salted `scrypt` hashes.
- `TRAKKO_ALLOW_REGISTRATION` to close registration (always possible while there is no account).
- Settings: an **Account** section (signed-in user, Sign out) and an **About** section with the
  credits and a link to the GitHub repository.
- New dark graphite and amber theme with a light variant for devices set to light mode, new app
  icons and theme colors.

- **Themes.** Settings → Appearance: Automatic, Graphite, Midnight, Forest, Ember (dark), Paper and
  Sand (light). The choice is applied before the page is drawn and kept on the device as a copy.
- **Change password** (Settings → Account, `POST /api/v1/auth/password`). It asks for the current
  password and ends the user's other sessions.

- **Default calendar view** per user (Day, Week or Month), chosen in Settings → Tracks and saved in
  the account (`users.default_view`, migration `0003`; `GET`/`PATCH /api/v1/preferences`). The app
  opens with it on every device.
- **App version**: defined once in `app/__init__.py` (0.1.0), shown at the bottom of Settings
  (`GET /api/v1/about`) and reported by the OpenAPI document. A release tag that does not match it
  makes the Docker workflow fail.

### Changed
- **The theme now belongs to the account** (`users.theme`, migration `0004`; `theme` in
  `GET`/`PATCH /api/v1/preferences`), so it follows the user to every device. The device keeps a copy
  so the page is drawn in the right colors before anything loads. Users who had picked a theme before
  keep it: the first device to sign in hands its theme to the account.
- Credits have two links: the project (TRAKKO) and the author (Stefano Perna), each to its GitHub page.
- Appearance: the theme cards show only the name, and Automatic takes the whole row.
- Event Type colors: a palette of 24 colors plus the background and surface color of every theme (read
  from the stylesheet, so new themes add theirs). The custom color picker is gone; an older custom
  color stays selected as "Current color" until another one is chosen.
- Month view: larger cells drawn as a bordered grid.
- Month view: today's number stays readable when it is shown as a day of a neighboring month.
- Static files are always revalidated (`Cache-Control: no-cache` with an ETag), and the page reloads
  once when a new service worker takes over, so a page never runs scripts from another version.
- The session cookie now also carries a fingerprint of the user's password hash, so a password
  change invalidates the old cookies.
- Credits now show only Stefano Perna, linking to the GitHub repository; the About text and the
  separate GitHub button are gone.
- The iOS status bar style is `black`, which stays readable with both dark and light themes.
- The session cookie now identifies a user (`<user id>.<expiry>.<signature>`); `TRAKKO_SECRET_KEY`
  is optional (a random key is generated at startup, so sessions end on restart).
- The default Track is now one per user.
- Event Type emoji are now picked from a list in a bottom sheet (grouped, filtered to what the
  device can draw) instead of being typed into a text field. The API still accepts any emoji.
- API validation messages no longer start with pydantic's "Value error, " prefix.
- The service worker no longer stores copies of `/api/v1/export`; signing out and signing in also
  clear the cached API responses.

### Removed
- `TRAKKO_PASSWORD` and the shared-password mode: accounts replace it.

### Upgrade notice
- **Migration `0002` deletes all existing Tracks, Event Types and Entries.** Data created before
  accounts existed has no owner. Export it from Settings first, then create your account and import
  the file.
