FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TRAKKO_DB_PATH=/data/trakko.db

# Run as an unprivileged user; /data is owned by it so a named volume is writable out of the box.
RUN groupadd --system --gid 10001 trakko \
    && useradd --system --uid 10001 --gid trakko --home-dir /app --shell /usr/sbin/nologin trakko \
    && mkdir /data \
    && chown trakko:trakko /data

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

USER trakko

# The SQLite database lives here: mount a volume to keep it across containers.
VOLUME /data
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

# Apply database migrations, then serve. `exec` lets Uvicorn receive stop signals directly.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
