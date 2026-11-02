/** Show a banner while the browser or an API call reports that the server is unreachable. */
export function initOfflineBanner() {
  const banner = document.getElementById("offline-banner");

  function setOnline(online) {
    banner.hidden = online;
  }

  window.addEventListener("online", () => setOnline(true));
  window.addEventListener("offline", () => setOnline(false));
  window.addEventListener("trakko:connectivity", (event) => setOnline(event.detail.online));
  setOnline(navigator.onLine);
}
