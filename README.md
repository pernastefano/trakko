# TRAKKO

[![CI](https://github.com/pernastefano/trakko/actions/workflows/ci.yml/badge.svg)](https://github.com/pernastefano/trakko/actions/workflows/ci.yml)
[![Docker](https://github.com/pernastefano/trakko/actions/workflows/docker.yml/badge.svg)](https://github.com/pernastefano/trakko/actions/workflows/docker.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A mobile-first Progressive Web App to track daily events.

Define **Tracks** (for example "Menstrual Cycle" or "Workout"), give each its own **Event Types**
("Cycle Start", "Ovulation", "Running", "Gym"), and log **Entries** on a calendar with an optional
short note. Self-hosted, one SQLite file, no cloud. Several people can share one installation,
each with their own account and their own data.

<!-- Screenshots: add images of the Home calendar, the day editor and Statistics here. -->
> Screenshots: _coming soon_.

## Features

- **Calendar** with Day, Week and Month views (Month by default, weeks start on Monday). Swipe or
  use the arrows to change period; "Today" jumps back. Entries show as colored markers or icons.
- **Fast logging:** tap a day, tap an Event Type, Save, with an optional note. Edit or delete
  entries from the same sheet.
- **Tracks and Event Types** with names, colors (a palette that includes the theme backgrounds) and icons (none, emoji, or one
  or two letters/digits). Reorder them, choose the default Track, delete with a confirmation that
  shows what will be lost.
- **Statistics** per Track and period (month, year, all): count per Event Type, current and longest
  streak, days since the last entry, average interval, entries per week or month, and an activity
  heatmap, drawn as inline SVG.
- **Export and import** all data as JSON.
- **Themes:** choose one in Settings: Graphite (default), Midnight, Forest and Ember (dark), Paper
  and Sand (light), or Automatic to follow the device. The choice is remembered on that device.
- **Installable PWA:** manifest, icons, iOS support, safe-area insets, and an app shell that opens
  offline (changes need a connection).
- **REST API** under `/api/v1` with OpenAPI docs at `/docs`.
- **Accounts:** sign up, sign in, sign out and change your password; many users can share one
  installation and nobody sees anybody else's data. Registration can be switched off.

## Quick start (local)

Requires Python 3.12.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head            # create/upgrade the SQLite database
uvicorn app.main:app --reload
```

The app runs at http://localhost:8000 and `GET /health` returns `{"status": "ok"}`.

## Run with the container image

The image is built by GitHub Actions and published to the GitHub Container Registry:

```bash
docker run -d --name trakko -p 8000:8000 -v trakko-data:/data \
  -e TRAKKO_SECRET_KEY='<a long random value>' \
  ghcr.io/pernastefano/trakko:latest
```

Open it, tap **Create an account** and you are in. Keep `/data` on a volume. Production needs HTTPS
behind a reverse proxy; see
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Configuration

All configuration is done through environment variables (`.env.example` lists them; the app does not
read `.env` files itself).

| Variable | Default | Description |
|----------|---------|-------------|
| `TRAKKO_DB_PATH` | `data/trakko.db` (`/data/trakko.db` in the image) | Path of the SQLite database file. |
| `TRAKKO_SECRET_KEY` | _(random at every start)_ | Secret used to sign session cookies. Set it in production; without it a random key is generated and everyone is signed out whenever the app restarts. |
| `TRAKKO_ALLOW_REGISTRATION` | `true` | Whether new accounts can be created. Set to `false` once everyone has registered (it stays possible while no account exists). |

## Documentation

| Document | Contents |
|----------|----------|
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | Install on iOS/Android, Tracks, logging, calendar, statistics, export/import. |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Container, volume, environment variables, HTTPS and reverse proxy, backups. |
| [docs/API.md](docs/API.md) | REST endpoints with examples (full reference at `/docs`). |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Components, data model, request flow, service worker, design decisions. |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Setup, commands, tests and conventions. |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Branches, commits, pull requests. |
| [CHANGELOG.md](CHANGELOG.md) | Notable changes. |

## Development

```bash
pytest                          # run tests
ruff format . && ruff check .   # format + lint
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for the rest.

## License

MIT, see [LICENSE](LICENSE).
