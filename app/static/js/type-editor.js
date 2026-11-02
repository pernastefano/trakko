import { createEventType, deleteEventType, updateEventType } from "./api.js";
import { confirmAction } from "./confirm.js";
import { element } from "./dom.js";
import { createEmojiPicker } from "./emoji-picker.js";
import { createMarker } from "./markers.js";
import { THEMES } from "./theme.js";

const COLORS = [
  { name: "Red", value: "#ef4444" },
  { name: "Rose", value: "#f43f5e" },
  { name: "Pink", value: "#ec4899" },
  { name: "Fuchsia", value: "#d946ef" },
  { name: "Purple", value: "#a855f7" },
  { name: "Violet", value: "#8b5cf6" },
  { name: "Indigo", value: "#6366f1" },
  { name: "Blue", value: "#3b82f6" },
  { name: "Sky", value: "#0ea5e9" },
  { name: "Cyan", value: "#06b6d4" },
  { name: "Teal", value: "#14b8a6" },
  { name: "Emerald", value: "#10b981" },
  { name: "Green", value: "#22c55e" },
  { name: "Lime", value: "#84cc16" },
  { name: "Yellow", value: "#eab308" },
  { name: "Amber", value: "#f59e0b" },
  { name: "Orange", value: "#f97316" },
  { name: "Salmon", value: "#fb7185" },
  { name: "Peach", value: "#fdba74" },
  { name: "Mint", value: "#6ee7b7" },
  { name: "Light blue", value: "#93c5fd" },
  { name: "Brown", value: "#a16207" },
  { name: "Stone", value: "#78716c" },
  { name: "Gray", value: "#6b7280" },
];
const DEFAULT_COLOR = "#3b82f6";

/**
 * The background and surface colors of every theme, read from the stylesheet so that a new theme
 * adds its colors here without touching this file.
 */
function themeBackgrounds() {
  const probe = element("span");
  probe.hidden = true;
  document.body.append(probe);
  const colors = [];
  for (const theme of THEMES.filter((candidate) => candidate.id !== "auto")) {
    probe.dataset.theme = theme.id;
    const style = getComputedStyle(probe);
    for (const [variable, label] of [["--bg", "background"], ["--surface", "surface"]]) {
      colors.push({
        name: `${theme.name} ${label}`,
        value: style.getPropertyValue(variable).trim().toLowerCase(),
      });
    }
  }
  probe.remove();
  return colors.filter(
    (color, index) => /^#[0-9a-f]{6}$/.test(color.value) && colors.findIndex((other) => other.value === color.value) === index,
  );
}

const TEXT_ICON_LENGTH = 2;

/**
 * Dialog to create or edit an Event Type: name, color (from a fixed palette) and icon.
 * Calls `onChange()` after it saved or deleted something.
 */
export function createTypeEditor({ onChange }) {
  const dialog = document.getElementById("type-editor");
  const title = document.getElementById("type-editor-title");
  const form = document.getElementById("type-form");
  const name = document.getElementById("type-name");
  const preview = document.getElementById("type-preview");
  const swatches = document.getElementById("type-swatches");
  const themeSwatches = document.getElementById("type-theme-swatches");
  const iconField = document.getElementById("type-icon-field");
  const iconLabel = document.getElementById("type-icon-label");
  const iconValue = document.getElementById("type-icon-value");
  const emojiButton = document.getElementById("type-emoji-button");
  const error = document.getElementById("type-error");
  const saveButton = document.getElementById("type-save");
  const deleteButton = document.getElementById("type-delete");

  const emojiPicker = createEmojiPicker();
  const state = { trackId: null, eventType: null, color: DEFAULT_COLOR, emoji: "" };
  let busy = false;

  function iconKind() {
    return form.querySelector('input[name="icon-kind"]:checked').value;
  }

  function showError(message) {
    error.textContent = message ?? "";
    error.hidden = !message;
  }

  /** The icon text for the selected kind: a picked emoji, typed letters/digits, or nothing. */
  function iconText() {
    const kind = iconKind();
    if (kind === "emoji") return state.emoji;
    return kind === "text" ? iconValue.value.trim() : "";
  }

  function renderPreview() {
    const marker = createMarker({
      color: state.color,
      icon_kind: iconKind(),
      icon_value: iconText(),
    });
    preview.style.backgroundColor = marker.style.backgroundColor;
    preview.style.color = marker.style.color;
    preview.textContent = marker.textContent;
  }

  function renderEmojiButton() {
    emojiButton.replaceChildren(
      ...(state.emoji
        ? [element("span", "emoji-current", state.emoji), element("span", "", "Change")]
        : [element("span", "", "Choose an emoji")]),
    );
  }

  /** Emoji are picked from a list; letters and digits are typed. */
  function renderIconField() {
    const kind = iconKind();
    iconField.hidden = kind === "none";
    emojiButton.hidden = kind !== "emoji";
    iconValue.hidden = kind !== "text";
    if (kind === "none") return;
    iconLabel.textContent = kind === "emoji" ? "Emoji" : "Letter or number (1–2 characters)";
    iconLabel.htmlFor = kind === "emoji" ? emojiButton.id : iconValue.id;
    iconValue.maxLength = TEXT_ICON_LENGTH;
    renderEmojiButton();
  }

  function setColor(color) {
    state.color = color.toLowerCase();
    for (const radio of form.querySelectorAll('input[name="type-color"]')) {
      radio.checked = radio.value === state.color;
    }
    renderPreview();
  }

  function swatch({ name, value }) {
    const label = element("label", "swatch");
    const input = element("input");
    input.type = "radio";
    input.name = "type-color";
    input.value = value;
    input.setAttribute("aria-label", name);
    input.title = name;
    input.addEventListener("change", () => setColor(value));
    const dot = element("span");
    dot.style.backgroundColor = value;
    label.append(input, dot);
    return label;
  }

  /** Show the palette; a color that is no longer in it (older data) is offered first, as is. */
  function renderSwatches(currentColor) {
    const backgrounds = themeBackgrounds();
    const known = [...COLORS, ...backgrounds].some((color) => color.value === currentColor);
    const colors = known ? COLORS : [{ name: "Current color", value: currentColor }, ...COLORS];
    swatches.replaceChildren(...colors.map(swatch));
    themeSwatches.replaceChildren(...backgrounds.map(swatch));
  }

  function fill(eventType) {
    name.value = eventType?.name ?? "";
    const kind = eventType?.icon_kind ?? "none";
    form.querySelector(`input[name="icon-kind"][value="${kind}"]`).checked = true;
    state.emoji = kind === "emoji" ? eventType.icon_value : "";
    iconValue.value = kind === "text" ? eventType.icon_value : "";
    renderIconField();
    const color = (eventType?.color ?? DEFAULT_COLOR).toLowerCase();
    renderSwatches(color);
    setColor(color);
  }

  /** Open for a new Event Type of `trackId`, or to edit `eventType`. */
  function open({ trackId, eventType = null }) {
    Object.assign(state, { trackId, eventType });
    title.textContent = eventType ? "Edit event type" : "New event type";
    deleteButton.hidden = !eventType;
    showError(null);
    fill(eventType);
    dialog.showModal();
  }

  async function run(action) {
    busy = true;
    saveButton.disabled = deleteButton.disabled = true;
    showError(null);
    try {
      await action();
    } catch (failure) {
      showError(failure.message || "Something went wrong.");
      return;
    } finally {
      busy = false;
      saveButton.disabled = deleteButton.disabled = false;
    }
    dialog.close();
    onChange();
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (busy) return;
    const kind = iconKind();
    if (kind === "emoji" && !state.emoji) {
      showError("Choose an emoji, or pick another icon type.");
      return;
    }
    const data = { name: name.value, color: state.color, icon_kind: kind, icon_value: iconText() };
    run(() =>
      state.eventType
        ? updateEventType(state.eventType.id, data)
        : createEventType(state.trackId, data),
    );
  });

  deleteButton.addEventListener("click", async () => {
    const { eventType } = state;
    const count = eventType.entry_count;
    const entries = count === 1 ? "1 entry" : `${count} entries`;
    const accepted = await confirmAction({
      title: `Delete “${eventType.name}”?`,
      message:
        count === 0
          ? "This event type has no entries."
          : `Its ${entries} will be deleted too. This cannot be undone.`,
    });
    if (accepted) run(() => deleteEventType(eventType.id));
  });

  form.addEventListener("change", (event) => {
    if (event.target.name !== "icon-kind") return;
    iconValue.value = "";
    state.emoji = "";
    showError(null);
    renderIconField();
    renderPreview();
  });
  iconValue.addEventListener("input", renderPreview);
  emojiButton.addEventListener("click", async () => {
    const chosen = await emojiPicker.choose(state.emoji);
    if (!chosen) return;
    state.emoji = chosen;
    showError(null);
    renderEmojiButton();
    renderPreview();
  });
  document.getElementById("type-close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });

  return { open };
}
