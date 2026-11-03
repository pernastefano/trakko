import { updatePreferences } from "./api.js";
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

function option(theme, checked, onChoose) {
  // "Automatic" is the default choice: it takes the whole row, the others share it two by two.
  const label = element("label", theme.id === "auto" ? "theme-option theme-option-wide" : "theme-option");
  const input = element("input", "theme-input");
  input.type = "radio";
  input.name = "theme";
  input.value = theme.id;
  input.checked = checked;
  input.addEventListener("change", () => onChoose(theme.id));

  const card = element("span", "theme-card");
  card.append(swatch(theme), element("span", "theme-name", theme.name));
  label.append(input, card);
  return label;
}

/**
 * Apply the theme saved on this device and fill the theme picker in Settings.
 *
 * The theme belongs to the account. This device keeps a copy of it (so the page can be drawn in the
 * right colors before anything is loaded, and the sign-in screen has one too); `adopt()` brings
 * that copy in line with the account once it is known.
 */
export function initAppearance() {
  const picker = document.getElementById("theme-options");
  const error = document.getElementById("theme-error");

  function showError(message) {
    error.textContent = message ?? "";
    error.hidden = !message;
  }

  async function choose(id) {
    chooseTheme(id); // immediate, and remembered on this device
    showError(null);
    try {
      await updatePreferences({ theme: id });
    } catch {
      showError("Your account could not be updated: the theme is only applied on this device.");
    }
  }

  const current = savedTheme();
  applyTheme(current);
  picker.replaceChildren(...THEMES.map((theme) => option(theme, theme.id === current, choose)));

  return {
    /**
     * Follow the theme stored on the account. If none was ever chosen (`null`), this device's
     * theme becomes the account's, so a theme picked before accounts kept it is not lost.
     */
    async adopt(accountTheme) {
      if (accountTheme === null) {
        await updatePreferences({ theme: savedTheme() }).catch(() => {});
        return;
      }
      chooseTheme(accountTheme);
      const input = picker.querySelector(`input[value="${accountTheme}"]`);
      if (input) input.checked = true;
    },
  };
}
