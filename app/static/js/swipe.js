const MIN_DISTANCE = 50;
const HORIZONTAL_BIAS = 2;

/**
 * Call `onLeft` / `onRight` when the user swipes horizontally on `element`.
 * Mostly-vertical movements (scrolling) are ignored.
 */
export function onSwipe(element, { onLeft, onRight }) {
  let start = null;
  let swiped = false;

  element.addEventListener("pointerdown", (event) => {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    start = { x: event.clientX, y: event.clientY };
    swiped = false;
  });

  // A swipe that ends on the element it started from must not also count as a tap.
  element.addEventListener(
    "click",
    (event) => {
      if (!swiped) return;
      swiped = false;
      event.stopPropagation();
      event.preventDefault();
    },
    true,
  );

  element.addEventListener("pointercancel", () => {
    start = null;
  });

  element.addEventListener("pointerup", (event) => {
    if (start === null) return;
    const dx = event.clientX - start.x;
    const dy = event.clientY - start.y;
    start = null;

    if (Math.abs(dx) < MIN_DISTANCE || Math.abs(dx) < HORIZONTAL_BIAS * Math.abs(dy)) return;
    swiped = true;
    // The click that may follow fires right after pointerup; later clicks are real taps.
    setTimeout(() => {
      swiped = false;
    }, 0);
    if (dx < 0) onLeft?.();
    else onRight?.();
  });
}
