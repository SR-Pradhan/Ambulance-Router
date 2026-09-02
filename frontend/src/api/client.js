// Every call to the backend goes through this file. Components never call
// fetch() directly, so there is exactly one place that knows the API's shape,
// its base URL, and how errors are surfaced.

// Where the API lives.
//
// Deployed builds set VITE_API_URL (Vercel: Settings > Environment Variables).
// Vite inlines it at BUILD time, not run time, so changing it means triggering
// a redeploy, not just restarting anything.
//
// The fallback is local development: port 8001, not FastAPI's usual 8000,
// because another service on the dev machine already holds 8000. If you change
// it, update ALLOWED_ORIGINS in backend/app/main.py to match.
const BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8001")
  .replace(/\/$/, "");

// The admin key lives in sessionStorage, never in the bundle.
//
// Anything compiled into the JavaScript is public: you can read it out of the
// deployed bundle with one curl. So the key is typed by the operator and kept
// only for this browser tab. sessionStorage is cleared when the tab closes and
// is not shared with other tabs or sites.
//
// Honest limitation: sessionStorage is readable by any script running on the
// page, so it would not survive an XSS. A production system would use an
// httpOnly cookie the JavaScript cannot read. For a single-operator demo this
// is the right trade between safety and being able to refresh without
// re-entering the key.
const ADMIN_KEY_STORAGE = "adminKey";

export const adminKey = {
  get() {
    try {
      return sessionStorage.getItem(ADMIN_KEY_STORAGE) || null;
    } catch {
      return null;
    }
  },
  set(value) {
    try {
      if (value) sessionStorage.setItem(ADMIN_KEY_STORAGE, value);
      else sessionStorage.removeItem(ADMIN_KEY_STORAGE);
    } catch {
      // Private mode blocks storage. The key still works for this page load.
    }
  },
  clear() {
    this.set(null);
  },
};

async function request(path, options = {}) {
  const { admin, ...rest } = options;

  const headers = { "Content-Type": "application/json" };
  // Only attach the key to calls that actually need it, so it is not sprayed
  // across every public request.
  if (admin) {
    const key = adminKey.get();
    if (key) headers["X-Admin-Key"] = key;
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    headers,
    ...rest,
  });

  if (!response.ok) {
    // FastAPI puts errors in `detail`: a string for HTTPException (404/400/503)
    // and a list of field errors for Pydantic validation failures (422).
    // Flatten both into one readable message.
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (Array.isArray(body.detail)) {
        message = body.detail
          .map((e) => `${e.loc?.slice(1).join(".") || "input"}: ${e.msg}`)
          .join("; ");
      }
    } catch {
      // Body was not JSON - keep the status line.
    }
    throw new Error(message);
  }

  return response.json();
}

export const api = {
  // Dispatch
  createRequest: (patient_lat, patient_lng, severity = "standard",
                  required_facility = null) =>
    request("/requests", {
      method: "POST",
      body: JSON.stringify({
        patient_lat,
        patient_lng,
        severity,
        required_facility,
      }),
    }),
  queue: () => request("/queue"),
  listRequests: (status = "active") =>
    request(`/requests?status=${encodeURIComponent(status)}`),
  completeRequest: (id) =>
    request(`/requests/${id}/complete`, { method: "PATCH", admin: true }),

  // Live tracking
  liveAmbulances: () => request("/ambulances/live"),

  // Hospitals and capacity
  listHospitals: () => request("/hospitals"),
  updateBeds: (id, available_beds) =>
    request(`/hospitals/${id}/beds`, {
      method: "PATCH",
      admin: true,
      body: JSON.stringify({ available_beds }),
    }),

  // Admin
  overview: () => request("/admin/overview"),

  // Road network, for drawing the graph
  route: (source, dest, algo = "compare") =>
    request(`/route?source=${source}&dest=${dest}&algo=${algo}`),
};
