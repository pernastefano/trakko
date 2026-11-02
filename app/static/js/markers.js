import { element } from "./dom.js";

function readableTextColor(hex) {
  const value = parseInt(hex.slice(1), 16);
  const red = (value >> 16) & 255;
  const green = (value >> 8) & 255;
  const blue = value & 255;
  return (0.299 * red + 0.587 * green + 0.114 * blue) / 255 > 0.6 ? "#111827" : "#ffffff";
}

/** Round badge in the Event Type color, showing its icon (emoji, letter or number) if any. */
export function createMarker(eventType) {
  const marker = element("span", "marker");
  marker.style.backgroundColor = eventType.color;
  marker.style.color = readableTextColor(eventType.color);
  if (eventType.icon_kind !== "none") marker.textContent = eventType.icon_value;
  marker.setAttribute("aria-hidden", "true");
  return marker;
}
