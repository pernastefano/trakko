"""The app's colors: a dark graphite and amber theme, with no violet or lilac anywhere."""

import colorsys
import json
import re
from pathlib import Path

from app.services.pwa import STATIC_DIR, TEMPLATES_DIR

CSS = (STATIC_DIR / "css" / "app.css").read_text()
ROOT = Path(__file__).resolve().parent.parent

# Hues from blue-violet to magenta (degrees): the indigo/purple/lilac family.
FORBIDDEN_HUES = (245, 335)
MIN_SATURATION = 0.12  # greys and near-greys are fine whatever their tint


def hue_and_saturation(color: str) -> tuple[float, float]:
    red, green, blue = (int(color[i : i + 2], 16) / 255 for i in (1, 3, 5))
    hue, _, saturation = colorsys.rgb_to_hls(red, green, blue)
    return hue * 360, saturation


def is_violet(color: str) -> bool:
    hue, saturation = hue_and_saturation(color)
    return saturation >= MIN_SATURATION and FORBIDDEN_HUES[0] <= hue <= FORBIDDEN_HUES[1]


def variables(block: str) -> dict[str, str]:
    return dict(re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{6})\b", block))


def dark_block() -> str:
    return CSS[CSS.index(":root") : CSS.index("@media (prefers-color-scheme: light)")]


def light_block() -> str:
    start = CSS.index("@media (prefers-color-scheme: light)")
    return CSS[start : CSS.index("*,\n*::before")]


def test_dark_is_the_default_and_light_follows_the_system() -> None:
    assert "color-scheme: dark;" in dark_block()
    assert "color-scheme: light;" in light_block()
    assert 'name="color-scheme" content="dark light"' in (TEMPLATES_DIR / "base.html").read_text()


def test_both_palettes_define_the_same_colors() -> None:
    dark, light = variables(dark_block()), variables(light_block())

    assert set(light) <= set(dark)
    assert {"--bg", "--surface", "--text", "--muted", "--border", "--accent", "--danger"} <= set(
        dark
    )


def test_no_color_in_the_stylesheet_is_violet() -> None:
    colors = set(re.findall(r"#[0-9a-fA-F]{6}\b", CSS))

    assert colors
    assert not [color for color in colors if is_violet(color)]


def test_the_accent_is_amber() -> None:
    for block in (dark_block(), light_block()):
        hue, saturation = hue_and_saturation(variables(block)["--accent"])
        assert 20 <= hue <= 45 and saturation > 0.5, "amber/orange expected"


def test_the_dark_theme_is_actually_dark() -> None:
    def lightness(color: str) -> float:
        return colorsys.rgb_to_hls(*(int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)))[1]

    dark = variables(dark_block())
    assert lightness(dark["--bg"]) < 0.15 and lightness(dark["--surface"]) < 0.2
    assert lightness(dark["--text"]) > 0.8


def test_text_is_readable_on_the_surface_in_both_themes() -> None:
    def luminance(color: str) -> float:
        channels = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

    def contrast(a: str, b: str) -> float:
        high, low = sorted((luminance(a), luminance(b)), reverse=True)
        return (high + 0.05) / (low + 0.05)

    for block in (dark_block(), light_block()):
        colors = {**variables(dark_block()), **variables(block)}
        assert contrast(colors["--text"], colors["--surface"]) >= 7
        assert contrast(colors["--muted"], colors["--surface"]) >= 4.5
        assert contrast(colors["--accent"], colors["--surface"]) >= 4.5
        assert contrast(colors["--accent-text"], colors["--accent"]) >= 4.5
        assert contrast(colors["--danger"], colors["--surface"]) >= 4.5


def test_browser_chrome_colors_match_the_theme() -> None:
    dark = variables(dark_block())
    light = variables(light_block())
    html = (TEMPLATES_DIR / "base.html").read_text()
    manifest = json.loads((STATIC_DIR / "manifest.webmanifest").read_text())

    assert f'name="theme-color" content="{dark["--surface"]}">' in html
    assert f'content="{light["--surface"]}" media="(prefers-color-scheme: light)"' in html
    assert manifest["theme_color"] == dark["--surface"]
    assert manifest["background_color"] == dark["--bg"]
    assert not any(is_violet(manifest[key]) for key in ("theme_color", "background_color"))


def test_icon_colors_are_not_violet() -> None:
    script = (ROOT / "scripts" / "generate_icons.py").read_text()
    colors = re.findall(r"(?:BACKGROUND|FOREGROUND|ACCENT) = \(0x(..), 0x(..), 0x(..)\)", script)

    assert len(colors) == 3
    assert not [c for c in colors if is_violet("#" + "".join(c))]
