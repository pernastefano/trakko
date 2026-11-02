const API_BASE = "/api/v1";
// Name of the service worker cache that holds copies of GET responses (see service-worker.js).
const API_CACHE_NAME = "trakko-api-v1";

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
  }
}

function reportConnectivity(online) {
  window.dispatchEvent(new CustomEvent("trakko:connectivity", { detail: { online } }));
}

async function request(method, path, body) {
  const options = { method, credentials: "same-origin", headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, options);
  } catch {
    reportConnectivity(false);
    throw new ApiError(0, "You are offline.");
  }

  // When the network is unreachable the service worker answers 503, or serves a flagged cached copy.
  reportConnectivity(response.status !== 503 && !response.headers.has("X-Trakko-Offline"));

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new ApiError(response.status, payload.detail || "Something went wrong.");
  }
  return response.status === 204 ? null : response.json();
}

export function getAuthStatus() {
  return request("GET", "/auth/status");
}

/** Forget cached API responses, so another account on this device never sees them offline. */
async function clearApiCache() {
  if ("caches" in window) await caches.delete(API_CACHE_NAME);
}

export async function login(username, password) {
  const status = await request("POST", "/auth/login", { username, password });
  await clearApiCache();
  return status;
}

export async function register(username, password) {
  const status = await request("POST", "/auth/register", { username, password });
  await clearApiCache();
  return status;
}

export function listTracks() {
  return request("GET", "/tracks");
}

export function listEventTypes(trackId) {
  return request("GET", `/tracks/${trackId}/event-types`);
}

/** Entries of a Track between two dates (inclusive, "YYYY-MM-DD"). */
export function listEntries({ trackId, from, to }) {
  const query = new URLSearchParams({ track_id: trackId, from, to });
  return request("GET", `/entries?${query}`);
}

export function createEntry(data) {
  return request("POST", "/entries", data);
}

export function updateEntry(id, data) {
  return request("PATCH", `/entries/${id}`, data);
}

export function deleteEntry(id) {
  return request("DELETE", `/entries/${id}`);
}

export function createTrack(name) {
  return request("POST", "/tracks", { name });
}

export function updateTrack(id, data) {
  return request("PATCH", `/tracks/${id}`, data);
}

export function deleteTrack(id) {
  return request("DELETE", `/tracks/${id}`);
}

export function reorderTracks(ids) {
  return request("PUT", "/tracks/order", { ids });
}

export function createEventType(trackId, data) {
  return request("POST", `/tracks/${trackId}/event-types`, data);
}

export function updateEventType(id, data) {
  return request("PATCH", `/event-types/${id}`, data);
}

export function deleteEventType(id) {
  return request("DELETE", `/event-types/${id}`);
}

export function reorderEventTypes(trackId, ids) {
  return request("PUT", `/tracks/${trackId}/event-types/order`, { ids });
}

export function exportData() {
  return request("GET", "/export");
}

/** Replace all data with the content of an export document. */
export function importData(document) {
  return request("POST", "/import", document);
}

export async function logout() {
  await request("POST", "/auth/logout");
  await clearApiCache();
}

/** Statistics for a Track: `ref` anchors the month/year, `today` is the current day. */
export function getStats({ trackId, period, ref, today }) {
  const query = new URLSearchParams({ track_id: trackId, period, ref, today });
  return request("GET", `/stats?${query}`);
}
