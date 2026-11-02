import { onSwipe } from "./swipe.js";

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
    onChange(tracks[index]);
  }

  prev.addEventListener("click", () => move(-1));
  next.addEventListener("click", () => move(1));
  onSwipe(bar, { onLeft: () => move(1), onRight: () => move(-1) });

  return {
    /** Show `list` and select the default Track. */
    setTracks(list) {
      tracks = list;
      index = Math.max(0, list.findIndex((track) => track.is_default));
      render();
      if (tracks[index]) onChange(tracks[index]);
    },
    current() {
      return tracks[index] ?? null;
    },
  };
}
