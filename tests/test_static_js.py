"""Static consistency checks for the vanilla JS front end.

There is no JavaScript runtime in the test setup, so these catch the typos that would otherwise only
show up in the browser: imports of names a module does not export, and ids missing from the page.
"""

import re
from pathlib import Path

import pytest

from app.schemas import NOTE_MAX_LENGTH
from app.services.pwa import STATIC_DIR, TEMPLATES_DIR

JS_DIR = STATIC_DIR / "js"
MODULES = sorted(JS_DIR.glob("*.js"))

IMPORT = re.compile(r'import\s*\{([^}]*)\}\s*from\s*"\./([\w-]+\.js)"')
EXPORT = re.compile(r"export\s+(?:async\s+)?(?:function|const|class|let)\s+(\w+)")
ELEMENT_ID = re.compile(r'getElementById\("([\w-]+)"\)')
DATA_ATTRIBUTE = re.compile(r'querySelectorAll\("\[(data-[\w-]+)\]"\)')


def exports_of(path: Path) -> set[str]:
    return set(EXPORT.findall(path.read_text()))


def test_there_are_modules_to_check() -> None:
    assert {path.name for path in MODULES} >= {"main.js", "calendar.js", "dates.js", "api.js"}


@pytest.mark.parametrize("module", MODULES, ids=lambda path: path.name)
def test_imports_resolve_to_existing_exports(module: Path) -> None:
    for names, target in IMPORT.findall(module.read_text()):
        target_path = JS_DIR / target
        assert target_path.exists(), f"{module.name} imports missing file {target}"
        wanted = {name.strip() for name in names.split(",") if name.strip()}
        missing = wanted - exports_of(target_path)
        assert not missing, f"{module.name} imports {sorted(missing)} not exported by {target}"


def test_every_module_is_used() -> None:
    imported = {target for module in MODULES for _, target in IMPORT.findall(module.read_text())}
    entry_points = {"main.js"}
    unused = {path.name for path in MODULES} - imported - entry_points
    # pwa.js and offline.js are imported by main.js through the same regex.
    assert not unused, f"modules never imported: {sorted(unused)}"


def test_every_element_looked_up_by_id_exists_in_the_page() -> None:
    html = (TEMPLATES_DIR / "index.html").read_text()
    page_ids = set(re.findall(r'\bid="([\w-]+)"', html))
    for module in MODULES:
        for element_id in ELEMENT_ID.findall(module.read_text()):
            assert element_id in page_ids, f"{module.name} looks up #{element_id}, not in the page"


def test_data_attributes_used_by_scripts_exist() -> None:
    """Selected `[data-x]` attributes must be in the page or set by a script (`dataset.x`)."""
    html = (TEMPLATES_DIR / "index.html").read_text()
    scripts = "\n".join(module.read_text() for module in MODULES)
    for module in MODULES:
        for attribute in DATA_ATTRIBUTE.findall(module.read_text()):
            parts = attribute.removeprefix("data-").split("-")
            dataset_name = parts[0] + "".join(part.capitalize() for part in parts[1:])
            in_page = f"{attribute}=" in html
            set_by_script = f"dataset.{dataset_name}" in scripts
            assert in_page or set_by_script, f"{module.name} selects [{attribute}], never set"


def test_calendar_controls_are_in_the_shell() -> None:
    html = (TEMPLATES_DIR / "index.html").read_text()

    for view in ("day", "week", "month"):
        assert f'data-cal-view="{view}"' in html
    assert re.search(r'data-cal-view="month" aria-pressed="true"', html), "Month is the default"
    for control in ("cal-prev", "cal-next", "cal-today", "cal-title", "cal-body"):
        assert f'id="{control}"' in html


def test_view_switcher_does_not_collide_with_calendar_markup() -> None:
    # views.js hides every `.content > [data-view]`; only the three screens may carry it.
    html = (TEMPLATES_DIR / "index.html").read_text()

    assert sorted(re.findall(r'data-view="(\w+)"', html)) == ["home", "settings", "stats"]


def test_day_editor_markup() -> None:
    html = (TEMPLATES_DIR / "index.html").read_text()

    assert '<dialog id="day-editor" class="sheet" aria-labelledby="editor-title">' in html
    # The textarea limit must follow the API's note limit.
    assert f'maxlength="{NOTE_MAX_LENGTH}"' in html
    for control in ("editor-save", "editor-delete", "editor-cancel", "editor-close", "editor-form"):
        assert f'id="{control}"' in html
    assert re.search(r'<button id="editor-save" type="submit"[^>]*\bdisabled\b', html)
    assert re.search(r'<button id="editor-delete" type="button"[^>]*\bhidden\b', html)


def test_editor_listens_to_the_event_the_calendar_dispatches() -> None:
    calendar = (JS_DIR / "calendar.js").read_text()
    editor = (JS_DIR / "editor.js").read_text()

    assert 'new CustomEvent("trakko:day-tap"' in calendar
    assert 'addEventListener("trakko:day-tap"' in editor


def test_settings_markup() -> None:
    html = (TEMPLATES_DIR / "index.html").read_text()

    for control in (
        "settings-tracks",
        "new-track-form",
        "export-button",
        "import-button",
        "import-file",
        "logout-button",
        "track-form",
        "make-default",
        "settings-types",
        "add-type",
        "delete-track",
        "type-editor",
        "type-form",
        "type-swatches",
        "type-color-custom",
        "type-icon-value",
        "confirm-dialog",
        "confirm-accept",
    ):
        assert f'id="{control}"' in html, control
    assert re.search(r'<input id="import-file" type="file" accept="[^"]*json[^"]*" hidden>', html)
    # The confirm dialog closes itself through its form, returning the pressed button's value.
    assert '<form method="dialog"' in html
    assert 'value="confirm"' in html and 'value="cancel"' in html


def test_icon_kinds_in_the_editor_match_the_api() -> None:
    html = (TEMPLATES_DIR / "index.html").read_text()

    assert sorted(re.findall(r'name="icon-kind" value="(\w+)"', html)) == ["emoji", "none", "text"]


def test_palette_colors_are_valid_hex_colors() -> None:
    palette = re.search(
        r"const PALETTE = \[(.*?)\];", (JS_DIR / "type-editor.js").read_text(), re.S
    )
    colors = re.findall(r'"([^"]+)"', palette.group(1))

    assert len(colors) >= 8
    assert all(re.fullmatch(r"#[0-9a-f]{6}", color) for color in colors)
    assert len(set(colors)) == len(colors)


def test_settings_routes_are_recognised_by_the_view_switcher() -> None:
    # "#/settings/tracks/3" must still select the settings view (first path segment).
    views = (JS_DIR / "views.js").read_text()
    settings = (JS_DIR / "settings.js").read_text()

    assert '.split("/")[0]' in views
    assert "#\\/settings(?:\\/tracks\\/(\\d+))?" in settings


def test_service_worker_never_caches_auth_or_export() -> None:
    script = (STATIC_DIR / "service-worker.js").read_text()

    assert '"/api/v1/auth/"' in script
    assert '"/api/v1/export"' in script


def test_api_cache_name_is_shared_by_page_and_service_worker() -> None:
    page_name = re.search(r'API_CACHE_NAME = "([^"]+)"', (JS_DIR / "api.js").read_text())
    worker_name = re.search(
        r'API_CACHE = "([^"]+)"', (STATIC_DIR / "service-worker.js").read_text()
    )

    assert page_name and worker_name
    assert page_name.group(1) == worker_name.group(1)
