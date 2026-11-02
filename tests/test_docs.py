"""Keep the documentation in step with the code (links, files, endpoints, settings)."""

import re
from pathlib import Path

import pytest

from app.main import app
from app.services.pwa import STATIC_DIR

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
MARKDOWN_FILES = [
    ROOT / "README.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "CHANGELOG.md",
    *sorted(DOCS.glob("*.md")),
]
REQUIRED = [
    "README.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "LICENSE",
    ".env.example",
    "docs/ARCHITECTURE.md",
    "docs/API.md",
    "docs/USER_GUIDE.md",
    "docs/DEPLOYMENT.md",
    "docs/DEVELOPMENT.md",
]


def ids(path: Path) -> str:
    return str(path.relative_to(ROOT))


def test_required_documents_exist_and_are_not_empty() -> None:
    for name in REQUIRED:
        path = ROOT / name
        assert path.exists(), f"{name} is missing"
        assert path.read_text().strip(), f"{name} is empty"


@pytest.mark.parametrize("path", MARKDOWN_FILES, ids=ids)
def test_relative_links_point_to_existing_files(path: Path) -> None:
    text = path.read_text()
    for target in re.findall(r"\]\(([^)\s]+)\)", text):
        if re.match(r"[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
            continue  # external link or in-page anchor
        file_part = target.split("#")[0]
        assert (path.parent / file_part).exists(), f"{ids(path)} links to missing {target}"


@pytest.mark.parametrize("path", MARKDOWN_FILES, ids=ids)
def test_code_fences_are_balanced(path: Path) -> None:
    fences = [line for line in path.read_text().splitlines() if line.startswith("```")]
    assert len(fences) % 2 == 0, f"{ids(path)} has an unclosed code fence"


@pytest.mark.parametrize("path", MARKDOWN_FILES, ids=ids)
def test_mermaid_diagrams_start_with_a_known_type(path: Path) -> None:
    for block in re.findall(r"```mermaid\n(.*?)```", path.read_text(), re.S):
        first = block.strip().splitlines()[0]
        assert re.match(r"(flowchart|erDiagram|sequenceDiagram|classDiagram)\b", first), first


def test_architecture_has_the_required_sections_and_diagrams() -> None:
    text = (DOCS / "ARCHITECTURE.md").read_text()

    for heading in (
        "## Components",
        "## Data model",
        "## Request flow",
        "## PWA and service worker",
    ):
        assert heading in text
    assert "```mermaid\nerDiagram" in text


# --- settings ---


def settings_in_code() -> set[str]:
    return set(re.findall(r'"(TRAKKO_[A-Z_]+)"', (ROOT / "app" / "config.py").read_text()))


def test_every_setting_is_documented_everywhere() -> None:
    settings = settings_in_code()
    assert settings, "no settings found in app/config.py"
    for name in ("README.md", "docs/DEPLOYMENT.md", ".env.example"):
        text = (ROOT / name).read_text()
        for setting in settings:
            assert setting in text, f"{setting} missing from {name}"


# Settings that no longer exist; only the changelog may mention them, to say they were removed.
REMOVED_SETTINGS = {"TRAKKO_PASSWORD"}


@pytest.mark.parametrize("path", MARKDOWN_FILES, ids=ids)
def test_docs_do_not_mention_unknown_settings(path: Path) -> None:
    mentioned = set(re.findall(r"\bTRAKKO_[A-Z_]+\b", path.read_text()))
    allowed = settings_in_code() | (REMOVED_SETTINGS if path.name == "CHANGELOG.md" else set())
    assert mentioned <= allowed, f"{ids(path)}: {mentioned - allowed}"


def test_removed_settings_are_gone_from_the_code_and_the_example_file() -> None:
    code = (ROOT / "app" / "config.py").read_text() + (ROOT / ".env.example").read_text()
    for name in REMOVED_SETTINGS:
        assert name not in code


# --- files and modules mentioned ---


def test_paths_mentioned_in_backticks_exist() -> None:
    pattern = re.compile(r"`((?:app|alembic|scripts|tests|docs)/[\w./-]*)`")
    for path in MARKDOWN_FILES:
        for mentioned in pattern.findall(path.read_text()):
            assert (ROOT / mentioned).exists(), f"{ids(path)} mentions missing {mentioned}"


def test_javascript_modules_listed_in_the_architecture_exist() -> None:
    text = (DOCS / "ARCHITECTURE.md").read_text()
    for module in set(re.findall(r"`([\w-]+\.js)`", text)):
        found = (STATIC_DIR / "js" / module).exists() or (STATIC_DIR / module).exists()
        assert found, f"ARCHITECTURE.md mentions missing {module}"


def test_every_javascript_module_is_in_the_architecture() -> None:
    text = (DOCS / "ARCHITECTURE.md").read_text()
    for module in (STATIC_DIR / "js").glob("*.js"):
        assert f"`{module.name}`" in text, f"{module.name} is not described in ARCHITECTURE.md"


# --- API reference ---


def normalized(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", path)


def openapi_operations() -> set[tuple[str, str]]:
    operations = set()
    for path, methods in app.openapi()["paths"].items():
        for method in methods:
            operations.add((method.upper(), normalized(path.removeprefix("/api/v1"))))
    return operations


def test_every_endpoint_in_the_api_tables_exists() -> None:
    rows = re.findall(
        r"^\|\s*(GET|POST|PUT|PATCH|DELETE)\s*\|\s*`([^`?]+)",
        (DOCS / "API.md").read_text(),
        re.M,
    )
    assert len(rows) == 20, "the API tables were not parsed as expected"
    operations = openapi_operations()
    for method, path in rows:
        assert (method, normalized(path)) in operations, f"API.md documents {method} {path}"


def test_every_api_operation_is_documented() -> None:
    text = (DOCS / "API.md").read_text()
    documented = {
        (method, normalized(path))
        for method, path in re.findall(
            r"^\|\s*(GET|POST|PUT|PATCH|DELETE)\s*\|\s*`([^`?]+)", text, re.M
        )
    }
    # Statistics, export and import are described in prose sections rather than tables.
    documented |= {("GET", "/stats"), ("GET", "/export"), ("POST", "/import")}
    assert openapi_operations() <= documented, openapi_operations() - documented
    assert "GET /stats?" in text and "`GET /export`" in text and "`POST /import`" in text


# --- changelog ---


def test_changelog_follows_keep_a_changelog() -> None:
    text = (ROOT / "CHANGELOG.md").read_text()

    assert "keepachangelog.com" in text
    assert "## [Unreleased]" in text
    assert "### Added" in text
