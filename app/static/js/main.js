import { listTracks } from "./api.js";
import { ensureAuthenticated } from "./auth.js";
import { createCalendar } from "./calendar.js";
import { createDayEditor } from "./editor.js";
import { initOfflineBanner } from "./offline.js";
import { registerServiceWorker } from "./pwa.js";
import { createSettings } from "./settings.js";
import { createStats } from "./stats.js";
import { createTrackSelector } from "./tracks.js";
import { initViews } from "./views.js";

const app = document.getElementById("app");
const loadError = document.getElementById("load-error");
const loadErrorMessage = document.getElementById("load-error-message");
const calendar = createCalendar();
const stats = createStats();
const trackSelector = createTrackSelector({
  onChange(track) {
    calendar.setTrack(track);
    stats.setTrack(track);
  },
});
createDayEditor({
  currentTrack: trackSelector.current,
  onChange() {
    calendar.refresh();
    stats.invalidate();
  },
});
const settings = createSettings();

function showLoadError(message) {
  loadErrorMessage.textContent = message;
  loadError.hidden = false;
}

async function load() {
  loadError.hidden = true;
  try {
    await ensureAuthenticated();
    app.hidden = false;
    trackSelector.setTracks(await listTracks());
    settings.activate();
  } catch (error) {
    app.hidden = false;
    showLoadError(error.message || "Could not load your data.");
  }
}

// Settings changed Tracks or Event Types: reload them, keeping the selected Track if possible.
window.addEventListener("trakko:data-changed", async () => {
  try {
    trackSelector.setTracks(await listTracks(), trackSelector.current()?.id);
  } catch (error) {
    showLoadError(error.message || "Could not reload your data.");
  }
});

initOfflineBanner();
initViews();
document.getElementById("load-retry").addEventListener("click", load);
registerServiceWorker();
load();
