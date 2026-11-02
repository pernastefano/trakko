// The server replaces the two placeholders below: a hash of the app shell files and the list of
// files to precache, so every change to the shell produces a new cache and drops the old one.
const VERSION = "__ASSET_VERSION__";
const PRECACHE_URLS = __PRECACHE_URLS__;

const SHELL_URL = "/";
const STATIC_CACHE = `trakko-static-${VERSION}`;
const API_CACHE = "trakko-api-v1";

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(STATIC_CACHE);
      // Bypass the HTTP cache so the precache never holds files from an older version.
      await cache.addAll(PRECACHE_URLS.map((url) => new Request(url, { cache: "reload" })));
      await self.skipWaiting();
    })(),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keep = new Set([STATIC_CACHE, API_CACHE]);
      for (const key of await caches.keys()) {
        if (key.startsWith("trakko-") && !keep.has(key)) await caches.delete(key);
      }
      await self.clients.claim();
    })(),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname.startsWith("/api/")) {
    event.respondWith(networkFirstApi(request, url));
  } else if (url.pathname.startsWith("/static/")) {
    event.respondWith(cacheFirst(request));
  } else if (request.mode === "navigate" && url.pathname === SHELL_URL) {
    event.respondWith(networkFirstShell(request));
  }
});

async function cacheFirst(request) {
  const cached = await caches.match(request, { cacheName: STATIC_CACHE });
  return cached || fetch(request);
}

async function networkFirstShell(request) {
  try {
    return await fetch(request);
  } catch {
    return caches.match(SHELL_URL, { cacheName: STATIC_CACHE });
  }
}

async function networkFirstApi(request, url) {
  // Authentication responses are never stored.
  const cacheable = !url.pathname.startsWith("/api/v1/auth/");
  try {
    const response = await fetch(request);
    if (response.ok && cacheable) {
      const cache = await caches.open(API_CACHE);
      await cache.put(request, response.clone());
    }
    return response;
  } catch {
    if (cacheable) {
      const cached = await caches.match(request, { cacheName: API_CACHE });
      if (cached) {
        // Flag stale data so the page can keep showing the offline banner.
        const headers = new Headers(cached.headers);
        headers.set("X-Trakko-Offline", "1");
        return new Response(cached.body, { status: cached.status, headers });
      }
    }
    return new Response(JSON.stringify({ detail: "You are offline." }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    });
  }
}
