import { createEntry, deleteEntry, listEntries, listEventTypes, updateEntry } from "./api.js";
import { formatDay } from "./dates.js";
import { element } from "./dom.js";
import { createMarker } from "./markers.js";

/**
 * Bottom sheet to add, edit and delete the entries of one day of the current Track.
 * Opens on `trakko:day-tap`; calls `onChange()` after every saved change.
 */
export function createDayEditor({ currentTrack, onChange }) {
  const dialog = document.getElementById("day-editor");
  const title = document.getElementById("editor-title");
  const list = document.getElementById("editor-entries");
  const noTypes = document.getElementById("editor-no-types");
  const form = document.getElementById("editor-form");
  const formTitle = document.getElementById("editor-form-title");
  const typeGroup = document.getElementById("editor-types");
  const note = document.getElementById("editor-note");
  const error = document.getElementById("editor-error");
  const saveButton = document.getElementById("editor-save");
  const deleteButton = document.getElementById("editor-delete");
  const cancelButton = document.getElementById("editor-cancel");

  const state = { date: null, trackId: null, eventTypes: [], entries: [], editingId: null };
  let busy = false;

  function selectedTypeId() {
    const checked = form.querySelector('input[name="event-type"]:checked');
    return checked ? Number(checked.value) : null;
  }

  function showError(message) {
    error.textContent = message ?? "";
    error.hidden = !message;
  }

  function updateControls() {
    const editing = state.editingId !== null;
    formTitle.textContent = editing ? "Edit entry" : "Add entry";
    deleteButton.hidden = cancelButton.hidden = !editing;
    saveButton.disabled = busy || selectedTypeId() === null;
    deleteButton.disabled = cancelButton.disabled = busy;
  }

  function renderEntries() {
    const items = state.entries.map((entry) => {
      const type = state.eventTypes.find((candidate) => candidate.id === entry.event_type_id);
      const button = element("button", "editor-entry");
      button.type = "button";
      button.setAttribute("aria-label", `Edit ${type.name} entry`);
      if (entry.id === state.editingId) button.classList.add("is-editing");
      button.append(createMarker(type), element("span", "editor-entry-name", type.name));
      if (entry.note) button.append(element("span", "editor-entry-note", entry.note));
      button.addEventListener("click", () => startEditing(entry));
      const item = element("li");
      item.append(button);
      return item;
    });
    list.replaceChildren(...items);
  }

  function renderTypes(selectedId) {
    const chips = state.eventTypes.map((type) => {
      const label = element("label", "chip");
      const input = element("input", "chip-input");
      input.type = "radio";
      input.name = "event-type";
      input.value = type.id;
      input.checked = type.id === selectedId;
      const body = element("span", "chip-body");
      body.append(createMarker(type), element("span", "", type.name));
      label.append(input, body);
      return label;
    });
    typeGroup.querySelectorAll(".chip").forEach((chip) => chip.remove());
    typeGroup.append(...chips);
  }

  /** Reset the form to "add" mode; a Track with a single Event Type has it preselected. */
  function resetForm() {
    state.editingId = null;
    note.value = "";
    showError(null);
    const only = state.eventTypes.length === 1 ? state.eventTypes[0].id : null;
    renderTypes(only);
    renderEntries();
    updateControls();
  }

  function startEditing(entry) {
    state.editingId = entry.id;
    note.value = entry.note ?? "";
    showError(null);
    renderTypes(entry.event_type_id);
    renderEntries();
    updateControls();
    form.scrollIntoView({ block: "nearest" });
  }

  async function load() {
    try {
      const [eventTypes, entries] = await Promise.all([
        listEventTypes(state.trackId),
        listEntries({ trackId: state.trackId, from: state.date, to: state.date }),
      ]);
      state.eventTypes = eventTypes;
      state.entries = entries;
    } catch (failure) {
      showError(failure.message || "Could not load this day.");
      return;
    }
    noTypes.hidden = state.eventTypes.length > 0;
    form.hidden = state.eventTypes.length === 0;
    resetForm();
  }

  async function open(date) {
    const track = currentTrack();
    if (!track) return;
    Object.assign(state, {
      date,
      trackId: track.id,
      eventTypes: [],
      entries: [],
      editingId: null,
    });
    title.textContent = formatDay(date);
    list.replaceChildren();
    noTypes.hidden = true;
    form.hidden = false;
    note.value = "";
    renderTypes(null);
    showError(null);
    updateControls();
    dialog.showModal();
    await load();
  }

  async function run(action) {
    busy = true;
    showError(null);
    updateControls();
    try {
      await action();
    } catch (failure) {
      busy = false;
      showError(failure.message || "Something went wrong.");
      updateControls();
      return;
    }
    busy = false;
    dialog.close();
    onChange();
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const eventTypeId = selectedTypeId();
    if (eventTypeId === null || busy) return;
    const text = note.value.trim() || null;
    run(() =>
      state.editingId === null
        ? createEntry({ event_type_id: eventTypeId, date: state.date, note: text })
        : updateEntry(state.editingId, { event_type_id: eventTypeId, note: text }),
    );
  });

  form.addEventListener("change", updateControls);
  deleteButton.addEventListener("click", () => run(() => deleteEntry(state.editingId)));
  cancelButton.addEventListener("click", resetForm);
  document.getElementById("editor-close").addEventListener("click", () => dialog.close());
  document.getElementById("editor-settings-link").addEventListener("click", () => dialog.close());
  // A click on the backdrop lands on the dialog element itself.
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  window.addEventListener("trakko:day-tap", (event) => open(event.detail.date));
}
