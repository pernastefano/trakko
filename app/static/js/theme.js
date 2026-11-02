export const THEMES = [
  { id: "auto", name: "Automatic" },
  { id: "graphite", name: "Graphite" },
  { id: "midnight", name: "Midnight" },
  { id: "forest", name: "Forest" },
  { id: "ember", name: "Ember" },
  { id: "paper", name: "Paper" },
  { id: "sand", name: "Sand" },
];

// The same key is read by theme-init.js before the page is drawn.
const STORAGE_KEY = "trakko.theme";
const DEFAULT_THEME = "auto";

function isTheme(id) {
  return THEMES.some((theme) => theme.id === id);
}

/** The saved theme id, or "auto". The choice belongs to this device, not to the account. */
export function savedTheme() {
  try {
    const id = localStorage.getItem(STORAGE_KEY);
    return isTheme(id) ? id : DEFAULT_THEME;
  } catch {
    return DEFAULT_THEME;
  }
}

/** Match the browser's own bar (address bar, status bar) to the page. */
function updateBrowserColor(id) {
  const surface = getComputedStyle(document.documentElement).getPropertyValue("--surface").trim();
  for (const meta of document.querySelectorAll('meta[name="theme-color"]')) {
    // Remember the automatic colors from the HTML so "Automatic" can restore them.
    meta.dataset.automatic ??= meta.content;
    meta.content = id === "auto" ? meta.dataset.automatic : surface;
  }
}

export function applyTheme(id) {
  const root = document.documentElement;
  if (id === "auto") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", id);
  updateBrowserColor(id);
}

/** Apply a theme and remember it on this device. */
export function chooseTheme(id) {
  const theme = isTheme(id) ? id : DEFAULT_THEME;
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Not saved, but it still applies until the page is closed.
  }
  applyTheme(theme);
}
