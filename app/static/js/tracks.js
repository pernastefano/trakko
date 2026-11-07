import { onSwipe } from "./swipe.js";

// The selected Track survives a page reload (some phones reload a web app when it is used), but
// not closing the app: a new start always opens on the default Track.
const STORAGE_KEY = "trakko.track";

function remembered() {
  try {
    return Number(sessionStorage.getItem(STORAGE_KEY)) || null;
  } catch {
    return null; // storage can be unavailable (e.g. private browsing)
  }
}

function remember(track) {
  try {
    if (track) sessionStorage.setItem(STORAGE_KEY, String(track.id));
  } catch {
    // Not remembering is harmless.
  }
}

/**
 * Track selector: previous/next buttons, swipe and a "2/5" position indicator.
 * Calls `onChange(track)` whenever the selected Track changes.
 */
export function createTrackSelector({ onChange }) {
  const bar = document.getElementById("track-bar");
  const name = document.getElementById("track-name");
  const position = document.getElementById("track-position");
  const prev = document.getElementById("track-prev");
  const next = document.getElementById("track-next");

  let tracks = [];
  let index = 0;

  function render() {
    const track = tracks[index];
    name.textContent = track ? track.name : "TRAKKO";
    position.textContent = tracks.length > 1 ? `${index + 1}/${tracks.length}` : "";
    prev.disabled = next.disabled = tracks.length < 2;
  }

  function move(step) {
    if (tracks.length < 2) return;
    index = (index + step + tracks.length) % tracks.length;
    render();
    remember(tracks[index]);
    onChange(tracks[index]);
  }

  prev.addEventListener("click", () => move(-1));
  next.addEventListener("click", () => move(1));
  onSwipe(bar, { onLeft: () => move(1), onRight: () => move(-1) });

  return {
    /**
     * Show `list`, selecting `keepId` (or else the Track remembered for this session) if it is
     * still there, otherwise the default Track.
     */
    setTracks(list, keepId = null) {
      tracks = list;
      const wanted = keepId ?? remembered();
      const kept = list.findIndex((track) => track.id === wanted);
      index = kept >= 0 ? kept : Math.max(0, list.findIndex((track) => track.is_default));
      render();
      remember(tracks[index]);
      if (tracks[index]) onChange(tracks[index]);
    },
    current() {
      return tracks[index] ?? null;
    },
  };
}
