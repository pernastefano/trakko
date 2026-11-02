/**
 * Register the service worker (served from the root so it controls the whole app).
 *
 * When a new version of the app is deployed, the page that is already open was built from the old
 * files. As soon as the new service worker takes over, reload once so the page and its scripts
 * come from the same version.
 */
export async function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return;

  const wasControlled = Boolean(navigator.serviceWorker.controller);
  let reloading = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    // The first install also changes the controller, but then there is nothing stale to replace.
    if (!wasControlled || reloading) return;
    reloading = true;
    location.reload();
  });

  try {
    await navigator.serviceWorker.register("/service-worker.js", { scope: "/" });
  } catch (error) {
    console.warn("Service worker registration failed", error);
  }
}
