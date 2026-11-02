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

Run with authentication locally to test the sign-in flow:

```bash
TRAKKO_PASSWORD=local-test TRAKKO_SECRET_KEY=local-test-key uvicorn app.main:app --reload
```

## Commands

| Task | Command |
|------|---------|
| Run the app | `uvicorn app.main:app --reload` |
| Create/upgrade the database | `alembic upgrade head` |
| New migration after changing `app/models.py` | `alembic revision --autogenerate -m "Describe the change"` |
| Run the tests | `pytest` |
| Format and lint | `ruff format . && ruff check .` |
| Regenerate the PWA icons | `python scripts/generate_icons.py` |

Run `pytest` and `ruff` before every commit; CI runs the same two checks.

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
use the CSS variables in `app.css` so light and dark mode keep working. Load data through `api.js`
only. Every file under `app/static/` and `app/templates/` is precached by the service worker, so a
new file is picked up automatically.

**Documentation.** Update the relevant file in `docs/`, the README and `CHANGELOG.md` in the same
change as the behavior (see [CONTRIBUTING.md](../CONTRIBUTING.md)).

## Tests

`pytest` runs everything under `tests/`:

| Area | Files |
|------|-------|
| Models and migrations | `test_models.py`, `test_migrations.py` |
| API | `test_api_tracks.py`, `test_api_event_types.py`, `test_api_entries.py`, `test_stats.py`, `test_data.py`, `test_auth.py` |
| App shell and PWA | `test_pwa.py`, `test_health.py`, `test_config.py` |
| Front-end consistency | `test_static_js.py` |
| Documentation | `test_docs.py` |

API tests use FastAPI's `TestClient` against a temporary SQLite file; the `client_factory` fixture
in `tests/conftest.py` builds clients with or without a password, and `tests/helpers.py` creates
Tracks, Event Types and Entries through the API.

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

## Database

Migrations live in `alembic/versions/`. The database file defaults to `data/trakko.db`
(git-ignored); point `TRAKKO_DB_PATH` elsewhere to keep experiments separate. To start over, delete
the file and run `alembic upgrade head` again.

## Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| `no such table` | Run `alembic upgrade head`. |
| The app exits with `TRAKKO_SECRET_KEY must be set` | `TRAKKO_PASSWORD` is set without a secret key. |
| A UI change does not show up | The service worker is serving the old shell; see above. |
| 401 on every request | A password is set and you are not signed in; sign in on `/`. |
