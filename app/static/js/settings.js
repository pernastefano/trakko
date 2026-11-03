import {
  createTrack,
  deleteTrack,
  getAbout,
  listEventTypes,
  listTracks,
  logout,
  reorderEventTypes,
  reorderTracks,
  updatePreferences,
  updateTrack,
} from "./api.js";
import { confirmAction } from "./confirm.js";
import { initDataTransfer } from "./data-transfer.js";
import { element, icon } from "./dom.js";
import { createMarker } from "./markers.js";
import { createPasswordDialog } from "./password.js";
import { createTypeEditor } from "./type-editor.js";

const ICON_UP = "M5 15l7-7 7 7";
const ICON_DOWN = "M5 9l7 7 7-7";
const ROUTE = /^#\/settings(?:\/tracks\/(\d+))?$/;

function plural(count, singular, pluralForm) {
  return `${count} ${count === 1 ? singular : pluralForm}`;
}

function moveButton(direction, label, disabled, onClick) {
  const button = element("button", "icon-btn");
  button.type = "button";
  button.dataset.move = direction;
  button.disabled = disabled;
  button.setAttribute("aria-label", `Move ${label} ${direction}`);
  button.append(icon(direction === "up" ? ICON_UP : ICON_DOWN));
  button.addEventListener("click", onClick);
  return button;
}

/** A list row: tap to open, with up/down buttons to reorder. */
function settingsRow({ marker, label, badge, detail, index, count, onOpen, onMove }) {
  const main = element("button", "settings-row-main");
  main.type = "button";
  if (marker) main.append(marker);
  main.append(element("span", "settings-row-name", label));
  if (badge) main.append(element("span", "badge", badge));
  if (detail) main.append(element("span", "settings-row-detail", detail));
  main.addEventListener("click", onOpen);

  const reorder = element("div", "reorder");
  reorder.append(
    moveButton("up", label, index === 0, () => onMove(-1)),
    moveButton("down", label, index === count - 1, () => onMove(1)),
  );
  const item = element("li", "settings-row");
  item.append(main, reorder);
  return item;
}

/** Keep keyboard focus on the row that was just moved, since the list is rebuilt. */
function focusMoved(list, index, direction) {
  const buttons = list.children[index]?.querySelectorAll("[data-move]") ?? [];
  const wanted = [...buttons].find((button) => button.dataset.move === direction);
  (wanted && !wanted.disabled ? wanted : [...buttons].find((b) => !b.disabled))?.focus();
}

function showError(node, message) {
  node.textContent = message ?? "";
  node.hidden = !message;
}

/**
 * Settings screens: the Track list with export/import, and one screen per Track with its Event
 * Types. Routes: `#/settings` and `#/settings/tracks/<id>`. Dispatches `trakko:data-changed`
 * whenever something was modified so the Home screen can reload.
 */
export function createSettings({ onDefaultViewChange }) {
  const homeScreen = document.getElementById("settings-home");
  const trackScreen = document.getElementById("settings-track");
  const trackList = document.getElementById("settings-tracks");
  const homeError = document.getElementById("settings-error");
  const newTrackForm = document.getElementById("new-track-form");
  const newTrackName = document.getElementById("new-track-name");
  const accountName = document.getElementById("account-name");
  const accountStatus = document.getElementById("account-status");
  const viewButtons = document.querySelectorAll("[data-default-view]");
  const appVersion = document.getElementById("app-version");

  const trackForm = document.getElementById("track-form");
  const trackNameInput = document.getElementById("track-name-input");
  const trackSave = document.getElementById("track-save");
  const defaultBadge = document.getElementById("default-badge");
  const makeDefault = document.getElementById("make-default");
  const typeList = document.getElementById("settings-types");
  const trackError = document.getElementById("track-error");
  const deleteTrackButton = document.getElementById("delete-track");

  let ready = false;
  let latestRoute = 0;
  let current = null; // { track, tracks, types } of the Track screen

  function notifyChanged() {
    window.dispatchEvent(new Event("trakko:data-changed"));
  }

  function changedAndRefresh() {
    notifyChanged();
    route();
  }

  const typeEditor = createTypeEditor({ onChange: changedAndRefresh });
  initDataTransfer({ onImported: changedAndRefresh });

  // --- Default calendar view ---

  function showDefaultView(view) {
    for (const button of viewButtons) {
      button.setAttribute("aria-pressed", String(button.dataset.defaultView === view));
    }
  }

  for (const button of viewButtons) {
    button.addEventListener("click", async () => {
      const view = button.dataset.defaultView;
      showError(homeError, null);
      try {
        await updatePreferences({ default_view: view });
      } catch (failure) {
        showError(homeError, failure.message);
        return;
      }
      showDefaultView(view);
      onDefaultViewChange(view);
    });
  }

  // --- Track list ---

  function renderTracks(tracks, focus = null) {
    trackList.replaceChildren(
      ...tracks.map((track, index) =>
        settingsRow({
          label: track.name,
          badge: track.is_default ? "Default" : null,
          index,
          count: tracks.length,
          onOpen: () => {
            location.hash = `#/settings/tracks/${track.id}`;
          },
          onMove: (delta) => moveTrack(tracks, index, delta),
        }),
      ),
    );
    if (focus) focusMoved(trackList, focus.index, focus.direction);
  }

  async function moveTrack(tracks, index, delta) {
    const ids = tracks.map((track) => track.id);
    [ids[index], ids[index + delta]] = [ids[index + delta], ids[index]];
    try {
      renderTracks(await reorderTracks(ids), {
        index: index + delta,
        direction: delta < 0 ? "up" : "down",
      });
      notifyChanged();
    } catch (failure) {
      showError(homeError, failure.message);
    }
  }

  async function showHome(token) {
    homeScreen.hidden = false;
    trackScreen.hidden = true;
    showError(homeError, null);
    try {
      const tracks = await listTracks();
      if (token === latestRoute) renderTracks(tracks);
    } catch (failure) {
      if (token === latestRoute) showError(homeError, failure.message);
    }
  }

  newTrackForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    showError(homeError, null);
    try {
      const track = await createTrack(newTrackName.value);
      newTrackName.value = "";
      notifyChanged();
      location.hash = `#/settings/tracks/${track.id}`;
    } catch (failure) {
      showError(homeError, failure.message);
    }
  });

  // --- Track screen ---

  function renderTypes(focus = null) {
    const { track, types } = current;
    typeList.replaceChildren(
      ...types.map((eventType, index) =>
        settingsRow({
          marker: createMarker(eventType),
          label: eventType.name,
          detail: plural(eventType.entry_count, "entry", "entries"),
          index,
          count: types.length,
          onOpen: () => typeEditor.open({ trackId: track.id, eventType }),
          onMove: (delta) => moveType(index, delta),
        }),
      ),
    );
    if (focus) focusMoved(typeList, focus.index, focus.direction);
  }

  async function moveType(index, delta) {
    const { track, types } = current;
    const ids = types.map((eventType) => eventType.id);
    [ids[index], ids[index + delta]] = [ids[index + delta], ids[index]];
    try {
      current.types = await reorderEventTypes(track.id, ids);
      renderTypes({ index: index + delta, direction: delta < 0 ? "up" : "down" });
      notifyChanged();
    } catch (failure) {
      showError(trackError, failure.message);
    }
  }

  function updateSaveState() {
    const name = trackNameInput.value.trim();
    trackSave.disabled = name === "" || name === current?.track.name;
  }

  async function showTrack(id, token) {
    homeScreen.hidden = true;
    trackScreen.hidden = false;
    showError(trackError, null);
    let tracks;
    let types;
    try {
      [tracks, types] = await Promise.all([listTracks(), listEventTypes(id)]);
    } catch (failure) {
      if (token !== latestRoute) return;
      if (failure.status === 404) location.hash = "#/settings";
      else showError(trackError, failure.message);
      return;
    }
    if (token !== latestRoute) return;
    const track = tracks.find((candidate) => candidate.id === id);
    if (!track) {
      location.hash = "#/settings";
      return;
    }
    current = { track, tracks, types };
    trackNameInput.value = track.name;
    defaultBadge.hidden = !track.is_default;
    makeDefault.hidden = track.is_default;
    deleteTrackButton.hidden = tracks.length < 2;
    updateSaveState();
    renderTypes();
  }

  async function run(action) {
    showError(trackError, null);
    try {
      await action();
    } catch (failure) {
      showError(trackError, failure.message);
      return;
    }
    changedAndRefresh();
  }

  trackNameInput.addEventListener("input", updateSaveState);
  trackForm.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!trackSave.disabled) run(() => updateTrack(current.track.id, { name: trackNameInput.value }));
  });
  makeDefault.addEventListener("click", () =>
    run(() => updateTrack(current.track.id, { is_default: true })),
  );
  document.getElementById("add-type").addEventListener("click", () => {
    typeEditor.open({ trackId: current.track.id });
  });
  deleteTrackButton.addEventListener("click", async () => {
    const { track, types } = current;
    const entries = types.reduce((total, eventType) => total + eventType.entry_count, 0);
    const accepted = await confirmAction({
      title: `Delete “${track.name}”?`,
      message: `Its ${plural(types.length, "event type", "event types")} and ${plural(entries, "entry", "entries")} will be deleted too. This cannot be undone.`,
    });
    if (!accepted) return;
    showError(trackError, null);
    try {
      await deleteTrack(track.id);
    } catch (failure) {
      showError(trackError, failure.message);
      return;
    }
    notifyChanged();
    location.hash = "#/settings";
  });

  // --- Routing and account ---

  function route() {
    const match = location.hash.match(ROUTE);
    if (!ready || !match) return;
    const token = ++latestRoute;
    if (match[1]) showTrack(Number(match[1]), token);
    else showHome(token);
  }

  const passwordDialog = createPasswordDialog({
    onChanged() {
      accountStatus.textContent = "Password changed.";
      accountStatus.hidden = false;
    },
  });
  document.getElementById("change-password-button").addEventListener("click", () => {
    accountStatus.hidden = true;
    passwordDialog.open();
  });

  document.getElementById("logout-button").addEventListener("click", async () => {
    try {
      await logout();
    } catch (failure) {
      showError(homeError, failure.message);
      return;
    }
    location.reload();
  });
  window.addEventListener("hashchange", route);

  return {
    /** Call once the user is authenticated; shows the screen the URL points to. */
    activate({ username, defaultView }) {
      ready = true;
      accountName.textContent = username ? `Signed in as ${username}` : "";
      showDefaultView(defaultView);
      route();
      getAbout()
        .then(({ version }) => {
          appVersion.textContent = `TRAKKO v${version}`;
          appVersion.hidden = false;
        })
        .catch(() => {});
    },
  };
}
