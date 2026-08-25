const STATUS_CHIP = {
  en_route: "chip chip-info",
  pending: "chip chip-warning",
  completed: "chip chip-good",
};

function statusLabel(status) {
  return status === "en_route" ? "En route" : status === "pending" ? "Pending" : "Completed";
}

export default function ResultsPanel({ result }) {
  if (!result) {
    return (
      <div className="panel">
        <div className="panel-head">
          <h2>Result</h2>
        </div>
        <p className="note">
          No request yet. Place a patient on the map and dispatch to see the chosen
          hospital, the road route and the estimated arrival time.
        </p>
      </div>
    );
  }

  const { hospital, route, ambulance, alternatives, total_eta_minutes, status } = result;

  return (
    <div className="panel">
      <div className="panel-head">
        <h2>
          Request {result.request_id}
          <span className={STATUS_CHIP[status] || "chip"}>{statusLabel(status)}</span>
        </h2>
      </div>

      <div className="result-hero">
        <div>
          <span className="label">Hospital</span>
          <strong>{hospital.name}</strong>
          <span className="sub">
            {hospital.travel_minutes} min in current traffic, {hospital.distance} km
            by road, {hospital.available_beds} of {hospital.total_beds} beds free
          </span>
        </div>
        <div>
          <span className="label">Total ETA</span>
          <strong>
            {total_eta_minutes != null ? `${total_eta_minutes} min` : "Not available"}
          </strong>
          <span className="sub">
            {ambulance
              ? ambulance.pickup_eta_minutes != null
                ? `${ambulance.pickup_eta_minutes} min pickup, ${route.eta_minutes} min transport`
                : `Ambulance ${ambulance.id} assigned from the queue`
              : "Waiting for an ambulance"}
          </span>
        </div>
      </div>

      <dl className="detail-list">
        <div>
          <dt>Route</dt>
          <dd>{route.path?.join(" to ") || "Not available"}</dd>
        </div>
        <div>
          <dt>Road distance</dt>
          <dd>{route.distance_km} km</dd>
        </div>
        <div>
          <dt>Travel time</dt>
          <dd>{route.eta_minutes} min including traffic</dd>
        </div>
        {result.required_facility && (
          <div>
            <dt>Required unit</dt>
            <dd>{result.required_facility}</dd>
          </div>
        )}
        <div>
          <dt>Units available</dt>
          <dd>{hospital.facilities?.join(", ") || "general only"}</dd>
        </div>
        {ambulance && (
          <div>
            <dt>Ambulance</dt>
            <dd>
              {ambulance.distance != null
                ? `${ambulance.id}, ${ambulance.distance} km away`
                : ambulance.id}
            </dd>
          </div>
        )}
      </dl>

      {!ambulance && (
        <p className="warn-text">
          No ambulance was free. The hospital is still assigned and the request is
          queued for triage.
        </p>
      )}

      {alternatives?.length > 0 && (
        <>
          <h3>Alternatives considered</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Hospital</th>
                  <th className="numeric">Minutes</th>
                  <th className="numeric">Road km</th>
                  <th className="numeric">Beds</th>
                  <th className="numeric">Score</th>
                </tr>
              </thead>
              <tbody>
                {alternatives.map((a) => (
                  <tr key={a.id}>
                    <td>{a.name}</td>
                    <td className="numeric">{a.travel_minutes}</td>
                    <td className="numeric">{a.distance}</td>
                    <td className="numeric">
                      {a.available_beds} of {a.total_beds}
                    </td>
                    <td className="numeric">{a.score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="note">
            The score combines travel time with how full the hospital is, both
            measured in minutes. A hospital with no spare capacity is ranked as if
            it were up to 3 minutes further away. Travel time includes traffic, so
            a nearer hospital can rank lower than a further one on a clear road.
            Hospitals with zero free beds are excluded before ranking.
          </p>
        </>
      )}
    </div>
  );
}
