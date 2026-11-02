# TRAKKO API

REST JSON under `/api/v1`. The full, always up-to-date reference is the OpenAPI document served at
`/docs` (Swagger UI) and `/openapi.json`; this page gives an overview and examples.

## Conventions

- Request and response bodies are JSON.
- Dates are plain calendar dates in `YYYY-MM-DD` (no time zone). Timestamps (`created_at`,
  `updated_at`) are UTC.
- Errors always have the shape `{ "detail": "..." }` with an English message.
  Validation errors (422) join the problems into one string, e.g. `"name: String should have at
  least 1 character"`.

| Status | Meaning                                                                  |
|--------|--------------------------------------------------------------------------|
| 200    | OK                                                                       |
| 201    | Created                                                                  |
| 204    | Done, no content (deletes, import, logout)                               |
| 401    | Not signed in, or wrong username or password                             |
| 403    | Registration is closed, or the current password is wrong                 |
| 404    | Resource not found                                                       |
| 409    | Conflict (e.g. deleting the only Track)                                  |
| 422    | Validation error or a rule of the domain was violated                    |

`GET /health` (outside `/api/v1`) returns `{"status": "ok"}`.

## Accounts and authentication

Every endpoint except `/health` and `/auth/*` needs a signed-in user: the `trakko_session` cookie
(HTTP-only, `SameSite=Lax`, 30 days, `Secure` over HTTPS) that registering or signing in sets. All
data belongs to a user: Tracks, Event Types, Entries, statistics, export and import only ever
concern the signed-in user's own data, and another user's ids answer `404` as if they did not exist.

| Method | Path             | Description                                                              |
|--------|------------------|--------------------------------------------------------------------------|
| GET    | `/auth/status`   | `{"authenticated": true, "username": "alice", "registration_open": true}` |
| POST   | `/auth/register` | Body `{"username", "password"}`; creates the account, signs in, adds a default Track (201). 409 if the name is taken, 403 if registration is closed |
| POST   | `/auth/login`    | Body `{"username", "password"}`; sets the cookie. 401 `Invalid username or password` whichever part is wrong |
| POST   | `/auth/password` | Body `{"current_password", "new_password"}` (204). 403 if the current password is wrong, 422 if the new one is invalid or equal to the old one. Ends the user's other sessions and renews this cookie |
| POST   | `/auth/logout`   | Clears the cookie (204)                                                  |

Usernames are case-insensitive (stored in lowercase), 3 to 32 characters: letters, digits, dots,
dashes and underscores, starting with a letter or digit. Passwords are 8 to 128 characters and are
stored as salted `scrypt` hashes. Registration is closed with `TRAKKO_ALLOW_REGISTRATION=false`,
but stays possible while no account exists so a new installation can always be set up.

## Tracks

| Method | Path                | Description                                                      |
|--------|---------------------|------------------------------------------------------------------|
| GET    | `/tracks`           | List, ordered by `position`                                      |
| POST   | `/tracks`           | Create `{"name"}`; appended last, the very first Track is the default |
| GET    | `/tracks/{id}`      | Read one                                                         |
| PATCH  | `/tracks/{id}`      | Rename (`name`) and/or `{"is_default": true}` to make it the default |
| PUT    | `/tracks/order`     | `{"ids": [3, 1, 2]}`, must list every Track exactly once         |
| DELETE | `/tracks/{id}`      | Deletes its Event Types and Entries too                          |

Rules: exactly one Track is the default. `is_default: false` on the default Track is rejected (422);
make another Track the default instead. Deleting the default Track promotes the first remaining one.
The only Track cannot be deleted (409).

```json
{ "id": 1, "name": "Workout", "position": 0, "is_default": true }
```

## Event types

| Method | Path                                  | Description                                  |
|--------|---------------------------------------|----------------------------------------------|
| GET    | `/tracks/{id}/event-types`            | List, ordered; includes `entry_count`        |
| POST   | `/tracks/{id}/event-types`            | Create                                       |
| PUT    | `/tracks/{id}/event-types/order`      | `{"ids": [...]}`, every Event Type once      |
| PATCH  | `/event-types/{id}`                   | Partial update                               |
| DELETE | `/event-types/{id}`                   | Deletes its Entries too                      |

```json
{
  "id": 4, "track_id": 1, "name": "Running", "color": "#ff7a00",
  "icon_kind": "emoji", "icon_value": "🏃", "position": 0, "entry_count": 12
}
```

Validation: `color` is `#rrggbb` (stored lowercase). `icon_kind` is `none`, `emoji` or `text`:

- `none`: `icon_value` must be empty (the default).
- `emoji`: a symbol or emoji, up to 16 characters, no letters, digits or spaces.
- `text`: one or two letters or digits.

On PATCH the resulting `(icon_kind, icon_value)` pair must be valid, so switching to `none` also
needs `"icon_value": ""`.

## Entries

| Method | Path             | Description                                                       |
|--------|------------------|-------------------------------------------------------------------|
| GET    | `/entries`       | Filters: `track_id`, `event_type_id`, `from`, `to` (inclusive)    |
| POST   | `/entries`       | `{"event_type_id", "date", "note"?}`                              |
| GET    | `/entries/{id}`  | Read one                                                          |
| PATCH  | `/entries/{id}`  | Change `event_type_id`, `date`, `note` (`null` clears the note)   |
| DELETE | `/entries/{id}`  | Delete                                                            |

```bash
curl -X POST localhost:8000/api/v1/entries \
  -H 'Content-Type: application/json' \
  -d '{"event_type_id": 4, "date": "2026-11-02", "note": "Easy 5k"}'

curl 'localhost:8000/api/v1/entries?track_id=1&from=2026-11-01&to=2026-11-30'
```

Notes are trimmed, blank becomes `null`, maximum 280 characters. Several entries on the same day
(even of the same Event Type) are allowed. Results are sorted by date, then id. An entry can only
be moved to an Event Type of the same Track.

## Statistics

`GET /stats?track_id=1&period=month&ref=2026-11-10&today=2026-11-10`

- `period`: `month` (default), `year` or `all`.
- `ref`: any date in the period to look at (default: `today`); the period is the month/year
  containing it.
- `today`: the current day, used for streaks and `days_since_last` (default: `ref`, or the server
  date when neither is given). Clients showing a past period pass their own date here.

Counts, `buckets` and `heatmap` cover the period. Streaks, `days_since_last` and
`average_interval_days` always use the whole history of the Event Type, with `today` as today.

- `buckets`: weekly (Monday start) for `month`, monthly for `year` and `all`; empty buckets are
  included. `all` spans the first to the last entry.
- A *streak* is a run of consecutive days with at least one entry. The current streak is alive when
  the last entry is `today` or the day before.
- `average_interval_days` is the mean gap between consecutive distinct days (`null` with fewer than
  two days).

```json
{
  "track_id": 1, "period": "month", "start": "2026-11-01", "end": "2026-11-30",
  "granularity": "week",
  "event_types": [{
    "event_type_id": 4, "name": "Running", "color": "#ff7a00", "icon_kind": "emoji",
    "icon_value": "🏃", "count": 4, "last_date": "2026-11-10", "days_since_last": 0,
    "current_streak": 2, "longest_streak": 2, "average_interval_days": 4.0
  }],
  "buckets": [{ "start": "2026-11-02", "count": 2 }],
  "heatmap": [{ "date": "2026-11-02", "count": 2 }]
}
```

## Export and import

`GET /export` returns the whole database as a nested document (no ids; list order is the order):

```json
{
  "version": 1,
  "exported_at": "2026-11-02T22:00:00Z",
  "tracks": [{
    "name": "Workout", "is_default": true,
    "event_types": [{
      "name": "Running", "color": "#ff7a00", "icon_kind": "emoji", "icon_value": "🏃",
      "entries": [{
        "date": "2026-11-02", "note": "Easy 5k",
        "created_at": "2026-11-02T21:00:00Z", "updated_at": "2026-11-02T21:00:00Z"
      }]
    }]
  }]
}
```

`POST /import` takes the same document and **replaces all existing data** in one transaction (204).
The document is validated first; if anything is invalid (422) nothing changes. It needs at least one
Track and exactly one default. `exported_at`, `created_at` and `updated_at` are optional.
