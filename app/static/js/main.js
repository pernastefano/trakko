import { getPreferences, listTracks } from "./api.js";
import { ensureAuthenticated } from "./auth.js";
import { initAppearance } from "./appearance.js";
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
const settings = createSettings({ onDefaultViewChange: calendar.setView });

function showLoadError(message) {
  loadErrorMessage.textContent = message;
  loadError.hidden = false;
}

async function load() {
  loadError.hidden = true;
  try {
    const status = await ensureAuthenticated();
    app.hidden = false;
    // A missing preference (e.g. offline with nothing cached) must not stop the app: Month it is.
    const [tracks, preferences] = await Promise.all([listTracks(), getPreferences().catch(() => null)]);
    const defaultView = preferences?.default_view ?? "month";
    calendar.setView(defaultView);
    if (preferences) appearance.adopt(preferences.theme);
    trackSelector.setTracks(tracks);
    settings.activate({ username: status?.username ?? null, defaultView });
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

const appearance = initAppearance();
initOfflineBanner();
initViews();
document.getElementById("load-retry").addEventListener("click", load);
registerServiceWorker();
load();
