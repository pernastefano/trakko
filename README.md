# TRAKKO

A mobile-first Progressive Web App to track daily events.

Define **Tracks** (e.g. "Menstrual Cycle", "Workout"), give each its own **Event Types**,
and log **Entries** on a calendar with an optional short note.

> Work in progress: only the project skeleton exists so far.

## Features

- Installable PWA (manifest, icons, iOS meta tags, safe-area insets), light and dark mode.
- App shell cached by a versioned service worker; offline banner when the server is unreachable.
- Track selector with arrows, swipe and a "2/5" indicator, and a bottom navigation bar.
- Calendar with Day, Week and Month views (Month by default, weeks start on Monday): swipe or use
  the arrows to change period, "Today" to jump back, today highlighted, and colored markers/icons
  for the entries of the current Track.
- REST API for Tracks, Event Types, Entries, statistics and JSON export/import.
- Day editor (bottom sheet): tap a day, tap an event type, Save. Add an optional note, tap an
  existing entry to change its type or note, or delete it.

- Settings: create, rename, reorder (up/down buttons), set default and delete Tracks; per Track,
  create, edit, reorder and delete Event Types (name, palette or custom color, icon: none, emoji or
  one or two letters/digits). Deleting asks for confirmation and shows how many entries go with
  it. Export all data as a JSON file, import one back (replaces everything), and sign out when a
  password is set.

The statistics screen is still to come.

## Quick start (local)

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head            # create/upgrade the SQLite database
uvicorn app.main:app --reload
```

The app runs at http://localhost:8000 and `GET /health` returns `{"status": "ok"}`.
The REST API lives under `/api/v1`; interactive docs are at http://localhost:8000/docs
(overview in [docs/API.md](docs/API.md)).

## Configuration

All configuration is done through environment variables (see `.env.example`).

| Variable            | Default           | Description                                                  |
|---------------------|-------------------|--------------------------------------------------------------|
| `TRAKKO_DB_PATH`    | `data/trakko.db`  | Path of the SQLite database file.                            |
| `TRAKKO_PASSWORD`   | _(unset)_         | Shared secret; when unset the app runs without authentication. |
| `TRAKKO_SECRET_KEY` | _(unset)_         | Secret used to sign session cookies. Required when `TRAKKO_PASSWORD` is set (the app refuses to start without it). |

## Development

```bash
pytest                          # run tests
ruff format . && ruff check .   # format + lint
```

The PWA icons in `app/static/icons/` are generated with the standard library only; regenerate
them after changing the artwork:

```bash
python scripts/generate_icons.py
```

The service worker is served from `/service-worker.js`. Its cache name is a hash of the files in
`app/static/` and `app/templates/`, so any change to the shell makes browsers fetch a fresh copy and
drop the old cache automatically.

## License

MIT, see [LICENSE](LICENSE).
