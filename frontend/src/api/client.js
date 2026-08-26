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

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
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
  listRequests: () => request("/requests"),
  completeRequest: (id) => request(`/requests/${id}/complete`, { method: "PATCH" }),

  // Live tracking
  liveAmbulances: () => request("/ambulances/live"),

  // Hospitals and capacity
  listHospitals: () => request("/hospitals"),
  updateBeds: (id, available_beds) =>
    request(`/hospitals/${id}/beds`, {
      method: "PATCH",
      body: JSON.stringify({ available_beds }),
    }),

  // Admin
  overview: () => request("/admin/overview"),

  // Road network, for drawing the graph
  route: (source, dest, algo = "compare") =>
    request(`/route?source=${source}&dest=${dest}&algo=${algo}`),
};
