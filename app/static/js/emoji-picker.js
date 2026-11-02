import { element } from "./dom.js";
import { EMOJI_GROUPS } from "./emoji-data.js";

/**
 * Returns a function telling whether this device can draw an emoji: unsupported ones render as the
 * same "missing glyph" box, so they look identical to a character no font has.
 */
function createSupportCheck() {
  const size = 32;
  const context = document.createElement("canvas").getContext("2d", { willReadFrequently: true });
  if (!context) return () => true;
  context.canvas.width = context.canvas.height = size;
  context.font = `${size - 8}px sans-serif`;
  context.textBaseline = "top";

  const render = (text) => {
    context.clearRect(0, 0, size, size);
    context.fillText(text, 0, 0);
    return context.getImageData(0, 0, size, size).data;
  };
  const missing = render("\u{10FFFF}");
  return (emoji) => {
    const pixels = render(emoji);
    return pixels.some((value, index) => value !== missing[index]);
  };
}

/**
 * Emoji picker in a bottom sheet. `choose(current)` resolves with the selected emoji, or null if
 * the sheet was closed without choosing. Only emoji the device can draw are listed.
 */
export function createEmojiPicker() {
  const dialog = document.getElementById("emoji-picker");
  const groups = document.getElementById("emoji-groups");
  let built = false;

  function build() {
    const isSupported = createSupportCheck();
    const available = EMOJI_GROUPS.map((group) => ({
      name: group.name,
      emojis: group.emojis.filter(isSupported),
    })).filter((group) => group.emojis.length > 0);
    // If detection removed everything it is not to be trusted: offer the full list instead.
    const shown = available.length > 0 ? available : EMOJI_GROUPS;

    groups.replaceChildren(
      ...shown.map((group) => {
        const section = element("section", "emoji-group");
        section.append(element("h3", "emoji-group-title", group.name));
        const grid = element("div", "emoji-grid");
        for (const emoji of group.emojis) {
          const option = element("button", "emoji-option", emoji);
          option.type = "button";
          option.addEventListener("click", () => dialog.close(emoji));
          grid.append(option);
        }
        section.append(grid);
        return section;
      }),
    );
    built = true;
  }

  document.getElementById("emoji-close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });

  return {
    choose(current) {
      if (!built) build();
      for (const option of groups.querySelectorAll(".emoji-option")) {
        option.setAttribute("aria-pressed", String(option.textContent === current));
      }
      dialog.returnValue = "";
      return new Promise((resolve) => {
        dialog.addEventListener("close", () => resolve(dialog.returnValue || null), { once: true });
        dialog.showModal();
        groups.parentElement.scrollTop = 0;
      });
    },
  };
}
