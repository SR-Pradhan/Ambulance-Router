export default function ResultsPanel({ result }) {
  if (!result) {
    return (
      <div className="panel muted">
        <h2>Result</h2>
        <p>No request yet. Place a patient and dispatch to see the chosen hospital, route and ETA.</p>
      </div>
    );
  }

  const { hospital, route, ambulance, alternatives, total_eta_minutes, status } = result;

  return (
    <div className="panel">
      <h2>
        Request #{result.request_id} <span className={`tag ${status}`}>{status}</span>
      </h2>

      <div className="result-hero">
        <div>
          <span className="label">Hospital</span>
          <strong>{hospital.name}</strong>
          <span className="sub">
            {hospital.distance} km by road · {hospital.available_beds} beds free
          </span>
        </div>
        <div>
          <span className="label">Total ETA</span>
          <strong>{total_eta_minutes ?? "—"} min</strong>
          <span className="sub">
            {ambulance
              ? `${ambulance.pickup_eta_minutes} min pickup + ${route.eta_minutes} min transport`
              : "no ambulance available"}
          </span>
        </div>
      </div>

      <p className="sub">
        Route: {route.path?.join(" → ")} ({route.distance_km} km at{" "}
        {route.assumed_speed_kmh} km/h assumed)
      </p>

      {ambulance ? (
        <p className="sub">
          Ambulance {ambulance.id} · pickup {ambulance.distance} km via{" "}
          {ambulance.pickup_path?.join(" → ")}
        </p>
      ) : (
        <p className="warn">
          No ambulance was free. The hospital is still assigned and the request is
          queued as pending.
        </p>
      )}

      {alternatives?.length > 0 && (
        <>
          <h3>Alternatives considered</h3>
          <table>
            <thead>
              <tr>
                <th>Hospital</th>
                <th>Road km</th>
                <th>Beds</th>
              </tr>
            </thead>
            <tbody>
              {alternatives.map((a) => (
                <tr key={a.id}>
                  <td>{a.name}</td>
                  <td>{a.distance}</td>
                  <td>{a.available_beds}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="note">
            Hospitals with no free beds are excluded before ranking, so they never
            appear here.
          </p>
        </>
      )}
    </div>
  );
}
