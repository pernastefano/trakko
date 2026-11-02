import { element } from "./dom.js";
import { THEMES, applyTheme, chooseTheme, savedTheme } from "./theme.js";

function swatch(theme) {
  const box = element("span", "theme-swatch");
  // "Automatic" shows both of the themes it switches between.
  const shown = theme.id === "auto" ? ["graphite", "paper"] : [theme.id];
  for (const id of shown) {
    const chip = element("span", "theme-chip");
    chip.dataset.theme = id;
    box.append(chip);
  }
  return box;
}

function option(theme, checked) {
  // "Automatic" is the default choice: it takes the whole row, the others share it two by two.
  const label = element("label", theme.id === "auto" ? "theme-option theme-option-wide" : "theme-option");
  const input = element("input", "theme-input");
  input.type = "radio";
  input.name = "theme";
  input.value = theme.id;
  input.checked = checked;
  input.addEventListener("change", () => chooseTheme(theme.id));

  const card = element("span", "theme-card");
  card.append(swatch(theme), element("span", "theme-name", theme.name));
  label.append(input, card);
  return label;
}

/** Apply the saved theme and fill the theme picker in Settings. */
export function initAppearance() {
  const current = savedTheme();
  applyTheme(current);
  document
    .getElementById("theme-options")
    .replaceChildren(...THEMES.map((theme) => option(theme, theme.id === current)));
}
