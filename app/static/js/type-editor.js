import { createEventType, deleteEventType, updateEventType } from "./api.js";
import { confirmAction } from "./confirm.js";
import { element } from "./dom.js";
import { createMarker } from "./markers.js";

const PALETTE = [
  "#3b82f6", "#6366f1", "#a855f7", "#ec4899", "#ef4444", "#f97316",
  "#eab308", "#22c55e", "#14b8a6", "#78716c", "#6b7280", "#111827",
];

const ICON_FIELDS = {
  emoji: { label: "Emoji", maxLength: 16 },
  text: { label: "Letter or number (1–2 characters)", maxLength: 2 },
};

/**
 * Dialog to create or edit an Event Type: name, color (palette or custom) and icon.
 * Calls `onChange()` after it saved or deleted something.
 */
export function createTypeEditor({ onChange }) {
  const dialog = document.getElementById("type-editor");
  const title = document.getElementById("type-editor-title");
  const form = document.getElementById("type-form");
  const name = document.getElementById("type-name");
  const preview = document.getElementById("type-preview");
  const swatches = document.getElementById("type-swatches");
  const customColor = document.getElementById("type-color-custom");
  const iconField = document.getElementById("type-icon-field");
  const iconLabel = document.getElementById("type-icon-label");
  const iconValue = document.getElementById("type-icon-value");
  const error = document.getElementById("type-error");
  const saveButton = document.getElementById("type-save");
  const deleteButton = document.getElementById("type-delete");

  const state = { trackId: null, eventType: null, color: PALETTE[0] };
  let busy = false;

  function iconKind() {
    return form.querySelector('input[name="icon-kind"]:checked').value;
  }

  function showError(message) {
    error.textContent = message ?? "";
    error.hidden = !message;
  }

  function renderPreview() {
    const kind = iconKind();
    const marker = createMarker({
      color: state.color,
      icon_kind: kind,
      icon_value: kind === "none" ? "" : iconValue.value,
    });
    preview.style.backgroundColor = marker.style.backgroundColor;
    preview.style.color = marker.style.color;
    preview.textContent = marker.textContent;
  }

  function renderIconField() {
    const kind = iconKind();
    iconField.hidden = kind === "none";
    if (kind === "none") return;
    iconLabel.textContent = ICON_FIELDS[kind].label;
    iconValue.maxLength = ICON_FIELDS[kind].maxLength;
  }

  function setColor(color, { fromCustom = false } = {}) {
    state.color = color.toLowerCase();
    customColor.value = state.color;
    for (const radio of swatches.querySelectorAll("input")) {
      radio.checked = !fromCustom && radio.value === state.color;
    }
    renderPreview();
  }

  function renderSwatches() {
    swatches.replaceChildren(
      ...PALETTE.map((color) => {
        const label = element("label", "swatch");
        const input = element("input");
        input.type = "radio";
        input.name = "type-color";
        input.value = color;
        input.setAttribute("aria-label", color);
        input.addEventListener("change", () => setColor(color));
        const dot = element("span");
        dot.style.backgroundColor = color;
        label.append(input, dot);
        return label;
      }),
    );
  }

  function fill(eventType) {
    name.value = eventType?.name ?? "";
    const kind = eventType?.icon_kind ?? "none";
    form.querySelector(`input[name="icon-kind"][value="${kind}"]`).checked = true;
    iconValue.value = eventType?.icon_value ?? "";
    renderIconField();
    setColor(eventType?.color ?? PALETTE[0]);
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
    const data = {
      name: name.value,
      color: state.color,
      icon_kind: kind,
      icon_value: kind === "none" ? "" : iconValue.value.trim(),
    };
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
    renderIconField();
    renderPreview();
  });
  iconValue.addEventListener("input", renderPreview);
  customColor.addEventListener("input", () => setColor(customColor.value, { fromCustom: true }));
  document.getElementById("type-close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });

  renderSwatches();
  return { open };
}
