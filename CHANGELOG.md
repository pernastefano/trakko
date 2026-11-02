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
