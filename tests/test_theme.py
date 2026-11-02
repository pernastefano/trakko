"""The color themes: dark and light palettes, none of them violet, all readable."""

import colorsys
import json
import re
from pathlib import Path

import pytest

from app.services.pwa import STATIC_DIR, TEMPLATES_DIR

ROOT = Path(__file__).resolve().parent.parent
CSS = (STATIC_DIR / "css" / "app.css").read_text()
THEME_JS = (STATIC_DIR / "js" / "theme.js").read_text()

REQUIRED = {
    "--bg",
    "--surface",
    "--text",
    "--muted",
    "--border",
    "--accent",
    "--accent-text",
    "--danger",
    "--banner-bg",
    "--banner-text",
}

# Hues from blue-violet to magenta (degrees): the indigo/purple/lilac family.
FORBIDDEN_HUES = (245, 335)
MIN_SATURATION = 0.12  # greys and near-greys are fine whatever their tint


def rgb(color: str) -> tuple[float, float, float]:
    return tuple(int(color[i : i + 2], 16) / 255 for i in (1, 3, 5))  # type: ignore[return-value]


def hue_and_saturation(color: str) -> tuple[float, float]:
    hue, _, saturation = colorsys.rgb_to_hls(*rgb(color))
    return hue * 360, saturation


def lightness(color: str) -> float:
    return colorsys.rgb_to_hls(*rgb(color))[1]


def is_violet(color: str) -> bool:
    hue, saturation = hue_and_saturation(color)
    return saturation >= MIN_SATURATION and FORBIDDEN_HUES[0] <= hue <= FORBIDDEN_HUES[1]


def luminance(color: str) -> float:
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb(color)]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def rules() -> list[tuple[str, str]]:
    """(selector, declarations) of every innermost CSS rule."""
    return [(sel.strip(), body) for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", CSS)]


def variables(body: str) -> dict[str, str]:
    return dict(re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{6})\b", body))


def themes() -> dict[str, dict[str, str]]:
    """Every named theme in the stylesheet: id -> its variables (plus "scheme")."""
    found = {}
    for selector, body in rules():
        for theme_id in re.findall(r'(?<!:not\()\[data-theme="(\w+)"\]', selector):
            scheme = re.search(r"color-scheme:\s*(\w+)", body)
            found[theme_id] = {**variables(body), "scheme": scheme.group(1) if scheme else ""}
    return found


def listed_theme_ids() -> list[str]:
    return re.findall(r'\{ id: "(\w+)"', THEME_JS)


THEMES = themes()


# --- the list of themes ---


def test_there_are_several_themes_dark_and_light() -> None:
    schemes = [theme["scheme"] for theme in THEMES.values()]

    assert len(THEMES) >= 6
    assert schemes.count("dark") >= 3 and schemes.count("light") >= 2


def test_the_picker_lists_exactly_the_themes_the_stylesheet_defines() -> None:
    ids = listed_theme_ids()

    assert ids[0] == "auto"
    assert sorted(ids[1:]) == sorted(THEMES)
    assert len(ids) == len(set(ids))


def test_theme_ids_are_safe_for_the_early_script() -> None:
    # theme-init.js only accepts lowercase letters before the page is drawn.
    assert all(re.fullmatch(r"[a-z]+", theme_id) for theme_id in listed_theme_ids())


def test_early_script_and_module_use_the_same_storage_key() -> None:
    early = (STATIC_DIR / "js" / "theme-init.js").read_text()
    key = re.search(r'STORAGE_KEY = "([^"]+)"', THEME_JS).group(1)

    assert f'localStorage.getItem("{key}")' in early


# --- every theme ---


@pytest.mark.parametrize("theme_id", sorted(THEMES))
def test_theme_defines_every_variable(theme_id: str) -> None:
    theme = THEMES[theme_id]

    assert REQUIRED <= set(theme)
    assert theme["scheme"] in ("dark", "light")


@pytest.mark.parametrize("theme_id", sorted(THEMES))
def test_theme_colors_are_never_violet(theme_id: str) -> None:
    violet = [
        name
        for name, value in THEMES[theme_id].items()
        if value.startswith("#") and is_violet(value)
    ]

    assert not violet, violet


@pytest.mark.parametrize("theme_id", sorted(THEMES))
def test_theme_is_as_dark_or_as_light_as_it_claims(theme_id: str) -> None:
    theme = THEMES[theme_id]

    if theme["scheme"] == "dark":
        assert lightness(theme["--bg"]) < 0.15 and lightness(theme["--surface"]) < 0.2
        assert lightness(theme["--text"]) > 0.8
    else:
        assert lightness(theme["--bg"]) > 0.8 and lightness(theme["--surface"]) > 0.88
        assert lightness(theme["--text"]) < 0.2


@pytest.mark.parametrize("theme_id", sorted(THEMES))
def test_theme_text_is_readable(theme_id: str) -> None:
    theme = THEMES[theme_id]

    assert contrast(theme["--text"], theme["--surface"]) >= 7
    assert contrast(theme["--muted"], theme["--surface"]) >= 4.5
    assert contrast(theme["--accent"], theme["--surface"]) >= 4.5
    assert contrast(theme["--accent-text"], theme["--accent"]) >= 4.5
    assert contrast(theme["--danger"], theme["--surface"]) >= 4.5
    assert contrast(theme["--banner-text"], theme["--banner-bg"]) >= 4.5


def test_accents_are_distinct_across_themes() -> None:
    accents = [theme["--accent"] for theme in THEMES.values()]

    assert len(accents) == len(set(accents))


def test_no_color_in_the_stylesheet_is_violet() -> None:
    colors = set(re.findall(r"#[0-9a-fA-F]{6}\b", CSS))

    assert colors
    assert not [color for color in colors if is_violet(color)]


# --- Automatic ---


def automatic_dark() -> dict[str, str]:
    base = next(body for selector, body in rules() if selector.startswith(":root,"))
    return variables(base)


def automatic_light() -> dict[str, str]:
    body = next(body for selector, body in rules() if selector == ":root:not([data-theme])")
    return variables(body)


def test_automatic_is_graphite_or_paper_depending_on_the_device() -> None:
    assert automatic_dark() == {k: v for k, v in THEMES["graphite"].items() if k.startswith("--")}
    assert automatic_light() == {k: v for k, v in THEMES["paper"].items() if k.startswith("--")}
    assert "@media (prefers-color-scheme: light)" in CSS


def test_the_page_declares_support_for_both_schemes() -> None:
    assert 'name="color-scheme" content="dark light"' in (TEMPLATES_DIR / "base.html").read_text()


# --- browser chrome, manifest and icons ---


def test_browser_chrome_colors_match_the_automatic_theme() -> None:
    html = (TEMPLATES_DIR / "base.html").read_text()
    manifest = json.loads((STATIC_DIR / "manifest.webmanifest").read_text())
    graphite, paper = THEMES["graphite"], THEMES["paper"]

    assert f'name="theme-color" content="{graphite["--surface"]}">' in html
    assert f'content="{paper["--surface"]}" media="(prefers-color-scheme: light)"' in html
    assert manifest["theme_color"] == graphite["--surface"]
    assert manifest["background_color"] == graphite["--bg"]


def test_the_status_bar_style_works_for_dark_and_light_themes() -> None:
    # "black-translucent" would put white text over a light header.
    html = (TEMPLATES_DIR / "base.html").read_text()

    assert 'name="apple-mobile-web-app-status-bar-style" content="black"' in html


def test_icon_colors_are_not_violet() -> None:
    script = (ROOT / "scripts" / "generate_icons.py").read_text()
    colors = re.findall(r"(?:BACKGROUND|FOREGROUND|ACCENT) = \(0x(..), 0x(..), 0x(..)\)", script)

    assert len(colors) == 3
    assert not [c for c in colors if is_violet("#" + "".join(c))]
