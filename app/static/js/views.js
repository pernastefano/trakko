const VIEWS = ["home", "stats", "settings"];
// The Track selector only makes sense for views that work on one Track.
const VIEWS_WITH_TRACK_BAR = ["home", "stats"];

function currentView() {
  const name = location.hash.replace(/^#\/?/, "");
  return VIEWS.includes(name) ? name : "home";
}

/** Switch between Home, Statistics and Settings following the URL hash. */
export function initViews() {
  const trackBar = document.getElementById("track-bar");
  const sections = document.querySelectorAll(".content > [data-view]");
  const links = document.querySelectorAll("[data-nav]");

  function show() {
    const view = currentView();
    for (const section of sections) section.hidden = section.dataset.view !== view;
    for (const link of links) {
      if (link.dataset.nav === view) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    }
    trackBar.hidden = !VIEWS_WITH_TRACK_BAR.includes(view);
  }

  window.addEventListener("hashchange", show);
  show();
}
