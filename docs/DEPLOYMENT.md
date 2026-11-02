# Deployment

TRAKKO runs as one container (or one Uvicorn process) with one SQLite file. The container image is
built and published to the GitHub Container Registry (GHCR) by GitHub Actions; you never need
Docker to develop it.

## Run the container

```bash
docker run -d --name trakko \
  -p 8000:8000 \
  -v trakko-data:/data \
  -e TRAKKO_PASSWORD='choose-a-password' \
  -e TRAKKO_SECRET_KEY='<a long random value>' \
  --restart unless-stopped \
  ghcr.io/pernastefano/trakko:latest
```

Open `http://localhost:8000`. Generate a secret key with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Image tags

| Tag | Meaning |
|-----|---------|
| `latest` / `main` | The newest build of the `main` branch. |
| `sha-<commit>` | A specific commit. |
| `1.2.3`, `1.2` | Releases (git tags `v1.2.3`). Prefer a version tag in production. |

The image is built for `linux/amd64` and `linux/arm64` (so it runs on a Raspberry Pi or an ARM
NAS too) by the **Docker** workflow, on every push to `main` and every `v*` tag. Before publishing,
the workflow starts the image once and checks migrations, `/health`, the home page, the seeded
default Track and that it does not run as root. If you fork the repository, the first published
package is private: change its visibility in the package settings on GitHub to pull it without
logging in.

### Docker Compose

```yaml
services:
  trakko:
    image: ghcr.io/pernastefano/trakko:latest
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      TRAKKO_PASSWORD: ${TRAKKO_PASSWORD}
      TRAKKO_SECRET_KEY: ${TRAKKO_SECRET_KEY}
    volumes:
      - trakko-data:/data

volumes:
  trakko-data:
```

Put the two values in an `.env` file next to the compose file (Compose reads it, unlike TRAKKO
itself) and keep that file out of version control.

If the package is private, log in first: `echo <token> | docker login ghcr.io -u <user>
--password-stdin`, using a personal access token with the `read:packages` scope.

## Configuration

All settings are environment variables. TRAKKO does not read `.env` files by itself.

| Variable | Default | Description |
|----------|---------|-------------|
| `TRAKKO_DB_PATH` | `data/trakko.db` (`/data/trakko.db` in the image) | SQLite database file. Its directory is created if missing. |
| `TRAKKO_PASSWORD` | _(unset)_ | Shared password. **Unset means no authentication at all**, so always set it when the server is reachable from the internet. |
| `TRAKKO_SECRET_KEY` | _(unset)_ | Key that signs the session cookie. Required when `TRAKKO_PASSWORD` is set; the app refuses to start without it. Changing it signs everyone out. |

Never put these values in an image, a repository or a public issue.

## Data and backups

- **The database** is a single SQLite file, `/data/trakko.db` in the container. Keep `/data` on a
  volume so it survives upgrades and re-creation of the container.
- The container runs as the non-root user `trakko` (uid and gid `10001`). With a **named volume**
  this just works; with a **bind mount**, make the host directory writable by that user:
  `sudo chown 10001:10001 /path/to/data`.
- **Migrations run automatically** every time the container starts (`alembic upgrade head`), so
  upgrading is "pull the new image and start it".
- **Back up** by copying the database while the app is stopped, or online with SQLite's own tool:

  ```bash
  docker exec trakko python -c "import sqlite3; s=sqlite3.connect('/data/trakko.db'); \
  d=sqlite3.connect('/data/backup.db'); s.backup(d); d.close(); s.close()"
  docker cp trakko:/data/backup.db ./trakko-backup.db
  ```

  Users can also download everything from **Settings → Export JSON** and restore it with
  **Import JSON** (which replaces all data).

## Upgrading

```bash
docker pull ghcr.io/pernastefano/trakko:<version>
docker stop trakko && docker rm trakko
# run the same `docker run ...` command again (the volume keeps your data)
```

With Compose: `docker compose pull && docker compose up -d`. Take a backup first when upgrading
across versions; the [changelog](../CHANGELOG.md) lists schema changes. Browsers pick up a new
front-end version by themselves the next time the app is opened.

## HTTPS and reverse proxy

**Production needs HTTPS.** Browsers only install the app and run its service worker on secure
origins (`localhost` is exempt), and the sign-in cookie should never travel in clear text. Terminate
TLS in a reverse proxy in front of the container and publish only the proxy.

Two things the proxy must do:

1. **Forward the original scheme**, so the session cookie is marked `Secure`: send
   `X-Forwarded-Proto: https`, and tell Uvicorn to trust the proxy by setting the environment
   variable `FORWARDED_ALLOW_IPS` to the proxy's address (or `*` if the container is only reachable
   through the proxy). By default Uvicorn trusts only `127.0.0.1`.
2. **Pass `/service-worker.js` through without caching it**; the app already sends
   `Cache-Control: no-cache` for it.

### Caddy

```
trakko.example.com {
    reverse_proxy trakko:8000
}
```

Caddy gets a certificate automatically and sets the forwarded headers. Run Caddy and TRAKKO in the
same Docker network and start TRAKKO with `FORWARDED_ALLOW_IPS=*` (only the proxy can reach it).

### nginx

```nginx
server {
    listen 443 ssl http2;
    server_name trakko.example.com;
    # ssl_certificate / ssl_certificate_key ...

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

With the proxy on the same host, Uvicorn's default (`127.0.0.1`) already trusts it.

### Brute force

The sign-in endpoint has no built-in attempt limit. For an internet-facing instance use a long
password and rate-limit `POST /api/v1/auth/login` in the proxy (for example `limit_req` in nginx).

## Health check

`GET /health` returns `{"status": "ok"}` without authentication. The image's `HEALTHCHECK` uses it;
you can point a monitor at it too.

## Without Docker

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export TRAKKO_DB_PATH=/var/lib/trakko/trakko.db
export TRAKKO_PASSWORD=... TRAKKO_SECRET_KEY=...
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Run it under a process manager (for example a systemd service with `Restart=always`) behind the
same kind of reverse proxy.
