# Development guide

## Requirements

- Python **3.12** (`python3.12 --version`). On macOS with Homebrew it may not be on your `PATH`;
  use `/opt/homebrew/bin/python3.12` in that case.
- A modern browser for the front end. There is no Node.js, bundler or package manager for the
  JavaScript.
- Docker is **not** needed: the container image is built by GitHub Actions only.

## Setup

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head              # creates data/trakko.db and seeds one default Track
uvicorn app.main:app --reload     # http://localhost:8000
```

The app reads **environment variables only**; it does not load `.env` files. `.env.example`
documents the variables. To use it, export them yourself, for example:

```bash
set -a; source .env; set +a
```

You need an account to use the app: open it and tap **Create an account**. Without
`TRAKKO_SECRET_KEY` a random key is generated each time the app starts, so `--reload` signs you out;
set a fixed one while developing:

```bash
TRAKKO_SECRET_KEY=dev-key uvicorn app.main:app --reload
```

`TRAKKO_ALLOW_REGISTRATION=false` closes registration (it stays possible while the database has no
user).

## Commands

| Task | Command |
|------|---------|
| Run the app | `uvicorn app.main:app --reload` |
| Create/upgrade the database | `alembic upgrade head` |
| New migration after changing `app/models.py` | `alembic revision --autogenerate -m "Describe the change"` |
| Run the tests | `pytest` |
| Format and lint | `ruff format . && ruff check .` |
| Regenerate the PWA icons | `python scripts/generate_icons.py` |

Run `pytest` and `ruff` before every commit; CI runs the same checks (plus `ruff format --check`).

## Project layout

```
app/
  main.py          app factory, routers, error handlers, /static, /health
  config.py        settings from environment variables
  db.py            engine (foreign keys enabled), Base, session dependency
  models.py        SQLAlchemy models
  schemas.py       Pydantic schemas and validation rules
  deps.py          shared FastAPI dependencies (session, settings, require_auth)
  errors.py        domain exceptions
  routers/         HTTP layer (tracks, event_types, entries, stats, data, auth, pwa)
  services/        business logic
  templates/       base.html, index.html
  static/          css/, js/, icons/, manifest.webmanifest, service-worker.js
alembic/           migration environment and versions
scripts/           generate_icons.py
tests/             pytest suite
docs/              this documentation
```

## Making changes

**Backend.** Put rules in `app/services/`, keep routers thin, validate input in
`app/schemas.py`, and raise the exceptions from `app/errors.py` so they become
`{ "detail": "..." }` responses. Type hints everywhere. When a model changes, generate a migration,
read it (SQLite needs batch operations, `env.py` already enables them) and extend
`tests/test_migrations.py` if the schema rules changed.

**Front end.** Vanilla JavaScript as ES modules: no globals, no inline scripts, no frameworks,
no build step. Set text with `textContent`, label controls, keep touch targets at least 44 px, and
use the CSS variables in `app.css` so every theme keeps working (never hard-code a color). Load data through `api.js`
only. Every file under `app/static/` and `app/templates/` is precached by the service worker, so a
new file is picked up automatically.

**Documentation.** Update the relevant file in `docs/`, the README and `CHANGELOG.md` in the same
change as the behavior (see [CONTRIBUTING.md](../CONTRIBUTING.md)).

## Tests

`pytest` runs everything under `tests/`:

| Area | Files |
|------|-------|
| Models and migrations | `test_models.py`, `test_migrations.py` |
| API | `test_api_tracks.py`, `test_api_event_types.py`, `test_api_entries.py`, `test_stats.py`, `test_data.py` |
| Accounts | `test_auth.py`, `test_multiuser.py` |
| App shell and PWA | `test_pwa.py`, `test_health.py`, `test_config.py` |
| Front-end consistency | `test_static_js.py` |
| Container and workflows | `test_container.py` |
| Documentation | `test_docs.py` |

API tests use FastAPI's `TestClient` against a temporary SQLite file; the `client_factory` fixture
in `tests/conftest.py` builds clients, `sign_in("alice")` gives one signed in as a user (created with
a cheap password hash and no Track), and `tests/helpers.py` creates Tracks, Event Types and Entries
through the API. `tests/test_multiuser.py` checks that two users never see each other's data.

There is no JavaScript runtime in the test setup, so the browser code is not executed by `pytest`.
`tests/test_static_js.py` catches the mistakes that would otherwise only surface in the browser:
imports of names a module does not export, `getElementById` ids missing from the page, attributes
that nothing sets, and contracts between files (cache names, event names, API periods). The
behavior itself is verified by hand in the browser:

1. Start the app (`uvicorn app.main:app --reload`) with a throw-away `TRAKKO_DB_PATH`.
2. Check at phone width (about 375 px) and in both color schemes.
3. Exercise the flow you changed, including the error paths (invalid input, offline).

### Service worker while developing

The service worker caches the shell and the browser keeps using it between reloads. After editing
static files, reload twice, or unregister it in the browser's developer tools (Application →
Service Workers, and clear the `trakko-*` caches). The cache name changes whenever a shell file
changes, so a normal reload is enough in most cases.

## Container image and CI

Docker is not installed on the development machine and must not be run locally: the image is built
by GitHub Actions only.

| File | Purpose |
|------|---------|
| `Dockerfile`, `.dockerignore` | `python:3.12-slim`, non-root user, `/data` volume, runs `alembic upgrade head` and then Uvicorn on port 8000, `HEALTHCHECK` on `/health`. |
| `.github/workflows/ci.yml` | On pull requests and pushes to `main`: `ruff format --check`, `ruff check` and `pytest` on Python 3.12. |
| `.github/workflows/docker.yml` | On pushes to `main` and `v*` tags: build, smoke test, then push `linux/amd64` and `linux/arm64` images to `ghcr.io/pernastefano/trakko` with the workflow's `GITHUB_TOKEN`. |

Without Docker you can still check what the image needs: it installs only `requirements.txt`, so
create a clean virtual environment with just that file, copy `alembic.ini`, `alembic/` and `app/`
next to it, and run the image's command:

```bash
alembic upgrade head && uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`tests/test_container.py` guards the rest: every third-party import must be in `requirements.txt`,
the paths the Dockerfile copies must exist and not be ignored, and the workflow files must keep the
triggers, permissions and tags the documentation describes.

## Releasing

The version is defined once, as `__version__` in `app/__init__.py`; Settings, the OpenAPI document and
`GET /api/v1/about` all read it. To release `1.2.3`:

1. Set `__version__ = "1.2.3"` and, in `CHANGELOG.md`, turn "Unreleased" into `## [1.2.3] - <date>`
   (keep a fresh empty "Unreleased" above it).
2. Commit, then tag and push: `git tag v1.2.3 && git push --tags`.
3. The **Docker** workflow publishes `1.2.3` and `1.2` (and the tag fails if it does not match
   `__version__`, so a wrong tag never produces an image).

## Adding a theme

1. In `app/static/css/app.css` add a `[data-theme="<id>"]` block that sets all ten variables of the
   others (`--bg`, `--surface`, `--text`, `--muted`, `--border`, `--accent`, `--accent-text`,
   `--danger`, `--banner-bg`, `--banner-text`) and `color-scheme`.
2. Add `{ id, name }` to `THEMES` in `app/static/js/theme.js` (the id is lowercase letters only).
3. Add the id to `THEME_IDS` and to the `ThemeId` literal in `app/schemas.py`: that is the list the
   API accepts for a user's `theme`. No migration is needed (the column is not constrained).
4. Run `pytest tests/test_theme.py tests/test_preferences.py`: they check that the theme is complete,
   readable (contrast), as dark or light as it claims and free of violet, and that the stylesheet,
   the picker and the server list exactly the same themes.

## Database

Migrations live in `alembic/versions/`. The database file defaults to `data/trakko.db`
(git-ignored); point `TRAKKO_DB_PATH` elsewhere to keep experiments separate. To start over, delete
the file and run `alembic upgrade head` again.

## Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| `no such table` | Run `alembic upgrade head`. |
| You are signed out after every code change | No `TRAKKO_SECRET_KEY`: set one, see above. |
| A UI change does not show up | The service worker is serving the old shell; see above. |
| 401 on every request | You are not signed in; open `/` and sign in or create an account. |
