import json
import re
import struct
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.services import pwa

STATIC = pwa.STATIC_DIR


# --- app shell ---


def test_index_serves_the_shell_with_pwa_and_ios_metadata(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    html = response.text
    assert '<link rel="manifest" href="/static/manifest.webmanifest">' in html
    assert 'rel="apple-touch-icon"' in html
    assert 'name="apple-mobile-web-app-capable" content="yes"' in html
    assert "viewport-fit=cover" in html
    assert 'name="theme-color"' in html
    assert 'type="module" src="/static/js/main.js"' in html


def test_shell_has_no_inline_scripts_and_the_three_zones(client: TestClient) -> None:
    html = client.get("/").text

    assert not re.search(r"<script(?![^>]*\bsrc=)", html)
    assert 'id="track-bar"' in html
    assert 'id="view-home"' in html
    for target in ("#/", "#/stats", "#/settings"):
        assert f'href="{target}"' in html


def test_every_asset_referenced_by_the_shell_exists(client: TestClient) -> None:
    html = client.get("/").text

    for url in re.findall(r'(?:href|src)="(/static/[^"]+)"', html):
        assert client.get(url).status_code == 200, url


# --- manifest and icons ---


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


def test_manifest_is_served_with_the_right_type(client: TestClient) -> None:
    response = client.get("/static/manifest.webmanifest")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/manifest+json")


def test_manifest_fields() -> None:
    manifest = json.loads((STATIC / "manifest.webmanifest").read_text())

    assert manifest["name"] == "TRAKKO"
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == "/"
    assert manifest["theme_color"] and manifest["background_color"]
    purposes = {(icon["sizes"], icon["purpose"]) for icon in manifest["icons"]}
    assert ("192x192", "any") in purposes
    assert ("512x512", "any") in purposes
    assert ("512x512", "maskable") in purposes


def test_manifest_icons_exist_with_declared_sizes() -> None:
    manifest = json.loads((STATIC / "manifest.webmanifest").read_text())

    for icon in manifest["icons"]:
        width, height = map(int, icon["sizes"].split("x"))
        path = STATIC / icon["src"].removeprefix("/static/")
        assert png_size(path) == (width, height), icon["src"]


def test_apple_touch_icon_is_180px() -> None:
    assert png_size(STATIC / "icons" / "apple-touch-icon.png") == (180, 180)


# --- service worker ---


def test_service_worker_is_served_from_the_root_with_correct_headers(client: TestClient) -> None:
    response = client.get("/service-worker.js")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/javascript")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["service-worker-allowed"] == "/"


def test_service_worker_has_its_placeholders_filled(client: TestClient) -> None:
    script = client.get("/service-worker.js").text

    assert "__ASSET_VERSION__" not in script
    assert "__PRECACHE_URLS__" not in script
    urls = json.loads(re.search(r"const PRECACHE_URLS = (\[.*?\]);", script, re.S).group(1))
    assert urls[0] == "/"
    assert "/static/css/app.css" in urls
    assert "/static/js/main.js" in urls
    assert "/static/manifest.webmanifest" in urls
    assert "/static/icons/icon-192.png" in urls
    assert "/static/service-worker.js" not in urls


def test_every_precached_url_is_reachable(client: TestClient) -> None:
    for url in pwa.precache_urls():
        assert client.get(url).status_code == 200, url


# --- cache versioning ---


@pytest.fixture
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    static, templates = tmp_path / "static", tmp_path / "templates"
    (static / "js").mkdir(parents=True)
    templates.mkdir()
    (static / "service-worker.js").write_text(
        'const VERSION = "__ASSET_VERSION__";\nconst PRECACHE_URLS = __PRECACHE_URLS__;\n'
    )
    (static / "js" / "main.js").write_text("one")
    (static / ".hidden").write_text("ignored")
    (templates / "index.html").write_text("<html>")
    return static, templates


def test_version_is_stable_and_changes_with_any_shell_file(dirs: tuple[Path, Path]) -> None:
    static, templates = dirs
    first = pwa.asset_version(static, templates)

    assert pwa.asset_version(static, templates) == first
    (static / "js" / "main.js").write_text("two")
    after_static = pwa.asset_version(static, templates)
    (templates / "index.html").write_text("<html lang='en'>")
    after_template = pwa.asset_version(static, templates)

    assert len({first, after_static, after_template}) == 3


def test_version_ignores_hidden_files(dirs: tuple[Path, Path]) -> None:
    static, templates = dirs
    first = pwa.asset_version(static, templates)

    (static / ".hidden").write_text("changed")

    assert pwa.asset_version(static, templates) == first


def test_render_service_worker(dirs: tuple[Path, Path]) -> None:
    static, templates = dirs

    script = pwa.render_service_worker(static, templates)

    assert f'"{pwa.asset_version(static, templates)}"' in script
    assert 'const PRECACHE_URLS = ["/", "/static/js/main.js"];' in script


def test_static_files_must_be_revalidated(client: TestClient) -> None:
    for url in ("/static/js/main.js", "/static/css/app.css", "/static/manifest.webmanifest"):
        response = client.get(url)

        assert response.headers["cache-control"] == "no-cache", url
        assert response.headers["etag"], f"{url} needs an ETag to be revalidated cheaply"


def test_static_files_answer_304_when_unchanged(client: TestClient) -> None:
    first = client.get("/static/js/main.js")

    again = client.get("/static/js/main.js", headers={"If-None-Match": first.headers["etag"]})

    assert again.status_code == 304
