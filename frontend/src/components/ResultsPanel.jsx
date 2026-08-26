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

      {/* The journey as two legs, summarised.
          Raw node ids ("182 to 347 to 186...") mean nothing to a reader, so
          the summary leads with distance, time and a junction COUNT, and the
          full path is tucked behind a disclosure for when it is actually
          wanted. */}
      <div className="journey">
        {ambulance?.pickup_path && (
          <div className="journey-leg">
            <span className="journey-step">1</span>
            <div>
              <strong>Drive to the patient</strong>
              <span className="sub">
                {ambulance.distance} km · {ambulance.pickup_eta_minutes} min ·{" "}
                {ambulance.pickup_path.length} junctions
              </span>
            </div>
          </div>
        )}
        <div className="journey-leg">
          <span className="journey-step">{ambulance?.pickup_path ? 2 : 1}</span>
          <div>
            <strong>Carry the patient to hospital</strong>
            <span className="sub">
              {route.distance_km} km · {route.eta_minutes} min ·{" "}
              {route.path?.length ?? 0} junctions
            </span>
          </div>
        </div>
      </div>

      <dl className="detail-list">
        <div>
          <dt>Units available</dt>
          <dd>{hospital.facilities?.join(", ") || "general only"}</dd>
        </div>
        {result.required_facility && (
          <div>
            <dt>Required unit</dt>
            <dd>{result.required_facility}</dd>
          </div>
        )}
        {ambulance && (
          <div>
            <dt>Ambulance</dt>
            <dd>{ambulance.id}</dd>
          </div>
        )}
      </dl>

      {(ambulance?.pickup_path || route.path) && (
        <details className="path-detail">
          <summary>Show the junctions used</summary>
          {ambulance?.pickup_path && (
            <p className="sub">
              <strong>To the patient:</strong>{" "}
              {/* Reversed: dijkstra_all runs FROM the patient, so this path is
                  stored patient-first. The ambulance drives it the other way. */}
              {[...ambulance.pickup_path].reverse().join(" to ")}
            </p>
          )}
          <p className="sub">
            <strong>To the hospital:</strong> {route.path?.join(" to ")}
          </p>
          <p className="note">
            Numbers are road junction ids in the graph, not street names.
          </p>
        </details>
      )}

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
