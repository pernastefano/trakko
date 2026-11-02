"""Static consistency checks for the vanilla JS front end.

There is no JavaScript runtime in the test setup, so these catch the typos that would otherwise only
show up in the browser: imports of names a module does not export, and ids missing from the page.
"""

import re
from pathlib import Path

import pytest

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


def test_data_attributes_used_by_scripts_exist_in_the_page() -> None:
    html = (TEMPLATES_DIR / "index.html").read_text()
    for module in MODULES:
        for attribute in DATA_ATTRIBUTE.findall(module.read_text()):
            assert f"{attribute}=" in html, f"{module.name} selects [{attribute}], not in the page"


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
