/** Register the service worker (served from the root so it controls the whole app). */
export async function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return;
  try {
    await navigator.serviceWorker.register("/service-worker.js", { scope: "/" });
  } catch (error) {
    console.warn("Service worker registration failed", error);
  }
}
