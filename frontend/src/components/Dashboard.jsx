import { useState } from "react";

function Stat({ label, value, sub, tone }) {
  return (
    <div className={`stat ${tone || ""}`}>
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
      {sub && <span className="stat-sub">{sub}</span>}
    </div>
  );
}

export default function Dashboard({ overview, hospitals, requests, onUpdateBeds, onComplete }) {
  const [error, setError] = useState(null);

  const run = async (fn) => {
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(err.message);
    }
  };

  if (!overview) return <div className="panel muted">Loading dashboard…</div>;

  const { hospitals: h, ambulances: a, requests: r } = overview;

  return (
    <div className="dashboard">
      {error && <p className="error">{error}</p>}

      <div className="stats">
        <Stat label="Beds free" value={h.available_beds} sub={`of ${h.total_beds}`} />
        <Stat
          label="Occupancy"
          value={`${h.occupancy_percent}%`}
          tone={h.occupancy_percent > 85 ? "bad" : ""}
        />
        <Stat
          label="Accepting"
          value={h.accepting_patients}
          sub={`${h.full} full`}
          tone={h.full > 0 ? "warn" : ""}
        />
        <Stat
          label="Ambulances free"
          value={a.available}
          sub={`of ${a.count}`}
          tone={a.available === 0 ? "bad" : ""}
        />
        <Stat label="En route" value={r.en_route} />
        <Stat
          label="Awaiting ambulance"
          value={r.awaiting_ambulance}
          tone={r.awaiting_ambulance > 0 ? "warn" : ""}
        />
      </div>

      <div className="panel">
        <h2>Hospital capacity</h2>
        <p className="note">
          Setting a hospital to 0 free beds removes it from dispatch immediately —
          the ranking heap already filters on bed availability, so no routing code
          is involved.
        </p>
        <table>
          <thead>
            <tr>
              <th>Hospital</th>
              <th>Free</th>
              <th>Total</th>
              <th>Occupancy</th>
              <th>Status</th>
              <th>Adjust</th>
            </tr>
          </thead>
          <tbody>
            {hospitals.map((hosp) => (
              <tr key={hosp.id} className={hosp.accepting ? "" : "row-bad"}>
                <td>{hosp.name}</td>
                <td>{hosp.available_beds}</td>
                <td>{hosp.total_beds}</td>
                <td>{hosp.occupancy_percent}%</td>
                <td>
                  {hosp.accepting ? (
                    <span className="ok">accepting</span>
                  ) : (
                    <span className="bad">full</span>
                  )}
                </td>
                <td className="actions">
                  <button
                    onClick={() =>
                      run(() =>
                        onUpdateBeds(hosp.id, Math.max(0, hosp.available_beds - 1))
                      )
                    }
                    disabled={hosp.available_beds <= 0}
                  >
                    −
                  </button>
                  <button
                    onClick={() =>
                      run(() =>
                        onUpdateBeds(
                          hosp.id,
                          Math.min(hosp.total_beds, hosp.available_beds + 1)
                        )
                      )
                    }
                    disabled={hosp.available_beds >= hosp.total_beds}
                  >
                    +
                  </button>
                  <button
                    className="secondary"
                    onClick={() => run(() => onUpdateBeds(hosp.id, 0))}
                  >
                    Close
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="panel">
        <h2>Emergency requests</h2>
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Status</th>
              <th>Hospital</th>
              <th>Ambulance</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {requests.map((req) => (
              <tr key={req.id}>
                <td>{req.id}</td>
                <td>
                  <span className={`tag ${req.status}`}>{req.status}</span>
                </td>
                <td>{req.assigned_hospital_name || "—"}</td>
                <td>{req.assigned_ambulance_id ?? "—"}</td>
                <td>
                  {req.status !== "completed" && (
                    <button onClick={() => run(() => onComplete(req.id))}>
                      Complete
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {requests.length === 0 && (
              <tr>
                <td colSpan="5" className="muted">
                  No requests yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
        <p className="note">
          Completing a trip frees the ambulance and parks it at the hospital, so the
          next dispatch measures from where it actually is.
        </p>
      </div>
    </div>
  );
}
