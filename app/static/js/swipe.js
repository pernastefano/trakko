const MIN_DISTANCE = 50;
const HORIZONTAL_BIAS = 2;

/**
 * Call `onLeft` / `onRight` when the user swipes horizontally on `element`.
 * Mostly-vertical movements (scrolling) are ignored.
 */
export function onSwipe(element, { onLeft, onRight }) {
  let start = null;

  element.addEventListener("pointerdown", (event) => {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    start = { x: event.clientX, y: event.clientY };
  });

  element.addEventListener("pointercancel", () => {
    start = null;
  });

  element.addEventListener("pointerup", (event) => {
    if (start === null) return;
    const dx = event.clientX - start.x;
    const dy = event.clientY - start.y;
    start = null;

    if (Math.abs(dx) < MIN_DISTANCE || Math.abs(dx) < HORIZONTAL_BIAS * Math.abs(dy)) return;
    if (dx < 0) onLeft?.();
    else onRight?.();
  });
}
