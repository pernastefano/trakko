import { listTracks } from "./api.js";
import { ensureAuthenticated } from "./auth.js";
import { initOfflineBanner } from "./offline.js";
import { registerServiceWorker } from "./pwa.js";
import { createTrackSelector } from "./tracks.js";
import { initViews } from "./views.js";

const app = document.getElementById("app");
const loadError = document.getElementById("load-error");
const loadErrorMessage = document.getElementById("load-error-message");
const homeView = document.getElementById("view-home");

const trackSelector = createTrackSelector({
  onChange(track) {
    homeView.dataset.trackId = track.id;
  },
});

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
  } catch (error) {
    app.hidden = false;
    showLoadError(error.message || "Could not load your data.");
  }
}

initOfflineBanner();
initViews();
document.getElementById("load-retry").addEventListener("click", load);
registerServiceWorker();
load();
