const API_BASE = "/api/v1";

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

export function login(password) {
  return request("POST", "/auth/login", { password });
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
