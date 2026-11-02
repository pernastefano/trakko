# TRAKKO

A mobile-first Progressive Web App to track daily events.

Define **Tracks** (e.g. "Menstrual Cycle", "Workout"), give each its own **Event Types**,
and log **Entries** on a calendar with an optional short note.

> Work in progress: only the project skeleton exists so far.

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

## License

MIT, see [LICENSE](LICENSE).
