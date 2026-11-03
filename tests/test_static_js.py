"""Static consistency checks for the vanilla JS front end.

There is no JavaScript runtime in the test setup, so these catch the typos that would otherwise only
show up in the browser: imports of names a module does not export, and ids missing from the page.
"""

import re
from pathlib import Path
from typing import get_args

import pytest

from app.schemas import NOTE_MAX_LENGTH, CalendarView, Period, check_icon
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
    # main.js is the module entry point; theme-init.js is a plain script loaded by the page itself.
    entry_points = {"main.js", "theme-init.js"}
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
        "type-theme-swatches",
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


def palette() -> list[tuple[str, str]]:
    source = (JS_DIR / "type-editor.js").read_text()
    block = re.search(r"const COLORS = \[(.*?)\];", source, re.S).group(1)
    return re.findall(r'\{ name: "([^"]+)", value: "([^"]+)" \}', block)


def test_palette_colors_are_valid_hex_colors() -> None:
    colors = palette()

    assert len(colors) >= 20
    assert all(re.fullmatch(r"#[0-9a-f]{6}", value) for _, value in colors)
    assert len({value for _, value in colors}) == len(colors), "a color is listed twice"
    assert len({name for name, _ in colors}) == len(colors), "a name is used twice"


def test_the_default_color_is_in_the_palette() -> None:
    source = (JS_DIR / "type-editor.js").read_text()
    default = re.search(r'const DEFAULT_COLOR = "([^"]+)"', source).group(1)

    assert default in {value for _, value in palette()}


def test_there_is_no_custom_color_picker() -> None:
    html = (TEMPLATES_DIR / "index.html").read_text()
    editor = (JS_DIR / "type-editor.js").read_text()

    assert 'type="color"' not in html and "Custom color" not in html
    assert "customColor" not in editor and "type-color-custom" not in editor


def test_theme_backgrounds_are_offered_as_colors() -> None:
    """The colors of every theme's background and surface come from the stylesheet itself."""
    html = (TEMPLATES_DIR / "index.html").read_text()
    editor = (JS_DIR / "type-editor.js").read_text()

    assert 'id="type-theme-swatches"' in html and "Theme backgrounds" in html
    assert 'import { THEMES } from "./theme.js";' in editor
    assert '["--bg", "background"]' in editor and '["--surface", "surface"]' in editor
    # Every one of them is a plain #rrggbb color, which is what the API accepts.
    css = (STATIC_DIR / "css" / "app.css").read_text()
    for theme_id in re.findall(r'\{ id: "(\w+)"', (JS_DIR / "theme.js").read_text()):
        if theme_id == "auto":
            continue
        block = re.search(rf'\[data-theme="{theme_id}"\] \{{([^}}]*)\}}', css).group(1)
        for variable in ("--bg", "--surface"):
            assert re.search(rf"{variable}: #[0-9a-f]{{6}};", block), (theme_id, variable)


def test_palette_values_are_accepted_by_the_api() -> None:
    from pydantic import TypeAdapter

    from app.schemas import Color

    for _, value in palette():
        assert TypeAdapter(Color).validate_python(value) == value


def test_month_view_is_a_bordered_grid_with_roomy_cells() -> None:
    css = (STATIC_DIR / "css" / "app.css").read_text()
    month = re.search(r"\.month \{([^}]*)\}", css).group(1)
    day = re.search(r"\.month-day \{([^}]*)\}", css).group(1)

    # The gap shows the container's background, which draws the lines between the days.
    assert "gap: 1px" in month and "background: var(--border)" in month
    assert "border-radius: 12px" in month
    assert "background: var(--surface)" in day
    assert int(re.search(r"min-height: (\d+)px", day).group(1)) >= 64


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


def test_statistics_markup_matches_the_api_periods() -> None:
    html = (TEMPLATES_DIR / "index.html").read_text()

    periods = re.findall(r'data-stats-period="(\w+)"', html)
    assert periods == list(get_args(Period))
    assert re.search(r'data-stats-period="month" aria-pressed="true"', html), "Month is the default"
    for control in ("stats-prev", "stats-next", "stats-title", "stats-body"):
        assert f'id="{control}"' in html


def test_stats_request_sends_the_period_anchor_and_today() -> None:
    api = (JS_DIR / "api.js").read_text()
    stats = (JS_DIR / "stats.js").read_text()

    query = re.search(r"export function getStats.*?\n}\n", api, re.S).group(0)
    for parameter in ("track_id", "period", "ref", "today"):
        assert parameter in query
    assert "ref: state.anchor" in stats and "today: today()" in stats


def test_bar_chart_granularities_match_the_api() -> None:
    charts = (JS_DIR / "charts.js").read_text()

    assert 'granularity === "week"' in charts  # the API only returns "week" or "month"


# --- emoji picker ---


def emoji_groups() -> dict[str, list[str]]:
    source = (JS_DIR / "emoji-data.js").read_text()
    groups = re.findall(r'name: "([^"]+)",\s*emojis:\s*"([^"]+)"', source)
    return {name: emojis.split(" ") for name, emojis in groups}


def test_every_picker_emoji_is_accepted_by_the_api() -> None:
    groups = emoji_groups()
    assert len(groups) >= 5
    for name, emojis in groups.items():
        assert emojis, f"group {name} is empty"
        for emoji in emojis:
            check_icon("emoji", emoji)  # raises ValueError if the API would reject it


def test_picker_emoji_are_unique_and_single_symbols() -> None:
    every = [emoji for emojis in emoji_groups().values() for emoji in emojis]

    assert len(every) == len(set(every)), "an emoji is listed twice"
    assert all("‍" not in emoji for emoji in every), "joined sequences are not widely supported"
    assert all(not emoji.isascii() for emoji in every)


def test_emoji_are_picked_not_typed() -> None:
    html = (TEMPLATES_DIR / "index.html").read_text()
    editor = (JS_DIR / "type-editor.js").read_text()

    assert re.search(r'<button id="type-emoji-button" type="button"[^>]*\bhidden\b', html)
    for control in ("emoji-picker", "emoji-groups", "emoji-close"):
        assert f'id="{control}"' in html
    # For the emoji kind the value comes from the picker, never from the text input.
    assert 'if (kind === "emoji") return state.emoji;' in editor
    assert "emojiPicker.choose" in editor


# --- accounts, about and credits ---

REPOSITORY = "https://github.com/pernastefano/trakko"
PROJECT_URL = "https://github.com/pernastefano/trakko/"
AUTHOR_URL = "https://github.com/pernastefano/"


def test_sign_in_form_markup() -> None:
    html = (TEMPLATES_DIR / "index.html").read_text()

    for control in (
        "login-username",
        "login-password",
        "login-password-confirm",
        "login-submit",
        "login-switch",
        "login-hint",
    ):
        assert f'id="{control}"' in html, control
    assert 'autocomplete="username"' in html
    assert 'autocomplete="new-password"' in html
    # Creating an account asks for the password twice; signing in does not.
    assert re.search(r'id="login-confirm-field" class="login-field" hidden', html)


def test_the_form_follows_the_api_limits() -> None:
    html = (TEMPLATES_DIR / "index.html").read_text()

    assert 'id="login-username" name="username" type="text"' in html and 'maxlength="32"' in html
    assert 'maxlength="128"' in html


def test_settings_show_the_account_and_the_credits() -> None:
    html = (TEMPLATES_DIR / "index.html").read_text()

    for control in ("account-name", "account-status", "logout-button", "change-password-button"):
        assert f'id="{control}"' in html, control
    # Credits: exactly two links, the project and its author, and nothing else.
    credits = re.search(r'<h2 class="settings-heading">Credits</h2>\s*(.*?)\s*</ul>', html, re.S)
    assert credits, "Credits section missing"
    section = credits.group(1)
    assert re.findall(r'<a [^>]*href="([^"]+)"[^>]*>([^<]*)</a>', section) == [
        (PROJECT_URL, "TRAKKO"),
        (AUTHOR_URL, "Stefano Perna"),
    ]
    assert 'id="credits-project-link"' in section and 'id="credits-author-link"' in section
    labels = re.findall(r'<span class="credits-label">([^<]*)</span>', section)
    assert labels == ["Project", "Author"]
    assert re.sub(r"<[^>]+>", " ", section).split() == [
        "Project",
        "TRAKKO",
        "Author",
        "Stefano",
        "Perna",
    ]


def test_there_is_no_other_about_text_or_github_button() -> None:
    html = (TEMPLATES_DIR / "index.html").read_text()

    for removed in ("View the project on GitHub", "Built with", 'id="about"', 'id="github-link"'):
        assert removed not in html


def test_external_links_do_not_leak_the_opener() -> None:
    html = (TEMPLATES_DIR / "index.html").read_text()

    for link in re.findall(r"<a [^>]*href=\"https?://[^\"]+\"[^>]*>", html):
        assert 'target="_blank"' in link and "noopener" in link, link


def test_the_repository_link_matches_the_documentation() -> None:
    readme = (TEMPLATES_DIR.parent.parent / "README.md").read_text()

    assert "github.com/pernastefano/trakko" in readme


def test_the_signed_in_user_is_passed_to_settings() -> None:
    main = (JS_DIR / "main.js").read_text()
    settings = (JS_DIR / "settings.js").read_text()

    assert "settings.activate({ username: status?.username ?? null, defaultView })" in main
    assert "activate({ username, defaultView })" in settings


def test_page_script_clears_cached_data_when_the_account_changes() -> None:
    api = (JS_DIR / "api.js").read_text()

    assert api.count("await clearApiCache();") == 3  # sign in, register, sign out


# --- themes and password change ---


def test_theme_picker_and_early_script_are_in_the_page() -> None:
    base = (TEMPLATES_DIR / "base.html").read_text()
    html = (TEMPLATES_DIR / "index.html").read_text()

    assert 'id="theme-options"' in html and 'role="radiogroup"' in html
    # A plain, blocking script in <head>, after the stylesheet: the theme applies before painting.
    head = base[: base.index("</head>")]
    assert '<script src="/static/js/theme-init.js"></script>' in head
    assert head.index("app.css") < head.index("theme-init.js")
    assert 'type="module"' not in re.search(
        r"<script src=\"/static/js/theme-init.js\"[^>]*>", head
    ).group(0)


def test_theme_init_script_has_no_globals_and_no_imports() -> None:
    script = (JS_DIR / "theme-init.js").read_text()

    assert script.count("(function () {") == 1 and script.rstrip().endswith("})();")
    assert "import " not in script and "export " not in script


def test_password_dialog_markup() -> None:
    html = (TEMPLATES_DIR / "index.html").read_text()

    for control in (
        "password-dialog",
        "password-form",
        "password-current",
        "password-new",
        "password-confirm",
        "password-error",
        "password-save",
        "password-close",
    ):
        assert f'id="{control}"' in html, control
    assert (
        'id="password-current" class="text-input" type="password" autocomplete="current-password"'
        in html
    )
    assert html.count('autocomplete="new-password"') >= 3  # sign-up confirm, new, confirm new
    assert 'id="password-new"' in html and 'minlength="8"' in html


def test_password_change_request_matches_the_api() -> None:
    api = (JS_DIR / "api.js").read_text()

    assert 'request("POST", "/auth/password"' in api
    assert "current_password: currentPassword" in api and "new_password: newPassword" in api


def test_page_reloads_once_when_a_new_service_worker_takes_over() -> None:
    source = (JS_DIR / "pwa.js").read_text()

    assert 'addEventListener("controllerchange"' in source
    assert "location.reload()" in source
    # Not on the very first install, and never in a loop.
    assert "wasControlled" in source and "reloading" in source


# --- appearance picker ---


def test_theme_cards_show_only_the_title() -> None:
    themes = (JS_DIR / "theme.js").read_text()
    appearance = (JS_DIR / "appearance.js").read_text()
    css = (STATIC_DIR / "css" / "app.css").read_text()

    assert "hint" not in themes and "hint" not in appearance
    assert "theme-hint" not in css and "theme-label" not in css
    assert 'element("span", "theme-name", theme.name)' in appearance


def test_automatic_takes_the_whole_row() -> None:
    appearance = (JS_DIR / "appearance.js").read_text()
    css = (STATIC_DIR / "css" / "app.css").read_text()

    assert 'theme.id === "auto" ? "theme-option theme-option-wide"' in appearance
    wide = re.search(r"\.theme-option-wide \{([^}]*)\}", css).group(1)
    assert "grid-column: 1 / -1" in wide


def test_the_other_themes_fill_complete_rows_of_two() -> None:
    themes = re.findall(r'\{ id: "(\w+)"', (JS_DIR / "theme.js").read_text())
    grid = re.search(r"\.theme-options \{([^}]*)\}", (STATIC_DIR / "css" / "app.css").read_text())

    assert themes[0] == "auto"
    assert len(themes) - 1 == 6, "with Automatic on its own row, six themes make three rows of two"
    assert "minmax(152px, 1fr)" in grid.group(1)


def test_today_stays_readable_when_it_is_shown_as_a_day_of_a_neighboring_month() -> None:
    css = (STATIC_DIR / "css" / "app.css").read_text()

    # Outside days use the muted color for their number; today's highlighted circle must not.
    rule = re.search(r"\.month-day\.is-outside\.is-today \.month-number \{([^}]*)\}", css)
    assert rule and "color: var(--accent-text)" in rule.group(1)
    assert css.index(".month-day.is-outside .month-number") < css.index(rule.group(0))


# --- default calendar view and app version ---


def test_default_view_control_markup() -> None:
    html = (TEMPLATES_DIR / "index.html").read_text()

    group = re.search(
        r'<span id="default-view-label"[^>]*>(.*?)</span>\s*<div class="segmented"(.*?)</div>',
        html,
        re.S,
    )
    assert group, "default view control missing"
    assert group.group(1) == "Default calendar view"
    assert 'role="group" aria-labelledby="default-view-label"' in group.group(2)
    buttons = re.findall(r'data-default-view="(\w+)" aria-pressed="(\w+)"', group.group(2))
    assert [value for value, _ in buttons] == list(get_args(CalendarView))
    assert [value for value, pressed in buttons if pressed == "true"] == ["month"]


def test_default_view_control_lives_in_the_tracks_section() -> None:
    html = (TEMPLATES_DIR / "index.html").read_text()

    tracks = html.index('<h2 class="settings-heading">Tracks</h2>')
    control = html.index('id="default-view-label"')
    data = html.index('<h2 class="settings-heading">Data</h2>')
    assert tracks < control < data


def test_default_view_is_saved_through_the_preferences_api() -> None:
    api = (JS_DIR / "api.js").read_text()
    settings = (JS_DIR / "settings.js").read_text()

    assert 'request("GET", "/preferences")' in api
    assert 'request("PATCH", "/preferences", data)' in api
    assert "updatePreferences({ default_view: view })" in settings
    assert "onDefaultViewChange(view)" in settings
    # The button only looks selected once the server accepted the change.
    assert settings.index("await updatePreferences") < settings.index("showDefaultView(view);")


def test_default_view_is_applied_before_the_calendar_loads() -> None:
    main = (JS_DIR / "main.js").read_text()
    calendar = (JS_DIR / "calendar.js").read_text()

    assert "createSettings({ onDefaultViewChange: calendar.setView })" in main
    assert main.index("calendar.setView(defaultView)") < main.index(
        "trackSelector.setTracks(tracks)"
    )
    assert 'preferences?.default_view ?? "month"' in main, (
        "a missing preference falls back to Month"
    )
    assert "getPreferences().catch(() => null)" in main
    assert 'setView(view) {\n      if (!["day", "week", "month"].includes(view)' in calendar


def test_calendar_starts_on_month_until_told_otherwise() -> None:
    assert 'view: "month",' in (JS_DIR / "calendar.js").read_text()


def test_app_version_line_in_settings() -> None:
    html = (TEMPLATES_DIR / "index.html").read_text()
    settings = (JS_DIR / "settings.js").read_text()
    api = (JS_DIR / "api.js").read_text()

    assert '<p id="app-version" class="app-version" hidden></p>' in html
    assert html.index('id="credits-author-link"') < html.index('id="app-version"')
    assert 'request("GET", "/about")' in api
    assert "`TRAKKO v${version}`" in settings
    assert ".catch(() => {})" in settings, "a failed lookup must not break Settings"


# --- theme saved to the account ---


def test_choosing_a_theme_applies_it_then_saves_it_to_the_account() -> None:
    appearance = (JS_DIR / "appearance.js").read_text()

    assert 'import { updatePreferences } from "./api.js";' in appearance
    choose = re.search(r"async function choose\(id\) \{(.*?)\n  \}", appearance, re.S).group(1)
    assert choose.index("chooseTheme(id)") < choose.index("await updatePreferences({ theme: id })")
    assert "only applied on this device" in choose, "a failed save must be reported, not hidden"
    assert 'id="theme-error"' in (TEMPLATES_DIR / "index.html").read_text()


def test_the_account_theme_is_adopted_after_sign_in() -> None:
    appearance = (JS_DIR / "appearance.js").read_text()
    main = (JS_DIR / "main.js").read_text()

    assert "const appearance = initAppearance();" in main
    assert main.index("const appearance = initAppearance();") < main.index("\nload();")
    assert "if (preferences) appearance.adopt(preferences.theme);" in main
    adopt = re.search(r"async adopt\(accountTheme\) \{(.*?)\n    \},", appearance, re.S).group(1)
    # Nothing chosen on the account yet: the device's theme becomes the account's.
    assert "accountTheme === null" in adopt
    assert "updatePreferences({ theme: savedTheme() })" in adopt
    # Otherwise the account wins and the local copy follows it.
    assert "chooseTheme(accountTheme)" in adopt


def test_the_device_keeps_a_copy_of_the_theme_for_the_first_paint() -> None:
    early = (JS_DIR / "theme-init.js").read_text()
    theme = (JS_DIR / "theme.js").read_text()

    assert 'localStorage.getItem("trakko.theme")' in early
    assert "localStorage.setItem(STORAGE_KEY, theme)" in theme
