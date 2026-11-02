import hashlib
import json
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"

SERVICE_WORKER_FILE = "service-worker.js"
SHELL_URL = "/"


def _files(directory: Path) -> list[Path]:
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and not any(part.startswith(".") for part in path.parts)
    )


def asset_version(static_dir: Path = STATIC_DIR, templates_dir: Path = TEMPLATES_DIR) -> str:
    """Hash of everything the service worker caches, so any change yields a new cache."""
    digest = hashlib.sha256()
    for root in (static_dir, templates_dir):
        for path in _files(root):
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def precache_urls(static_dir: Path = STATIC_DIR) -> list[str]:
    urls = [
        f"/static/{path.relative_to(static_dir).as_posix()}"
        for path in _files(static_dir)
        if path.name != SERVICE_WORKER_FILE
    ]
    return [SHELL_URL, *urls]


def render_service_worker(
    static_dir: Path = STATIC_DIR, templates_dir: Path = TEMPLATES_DIR
) -> str:
    source = (static_dir / SERVICE_WORKER_FILE).read_text()
    return source.replace("__ASSET_VERSION__", asset_version(static_dir, templates_dir)).replace(
        "__PRECACHE_URLS__", json.dumps(precache_urls(static_dir))
    )
