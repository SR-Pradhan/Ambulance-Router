import { useState } from "react";
import AdminLock from "./AdminLock";

function Stat({ label, value, sub, tone, subTone }) {
  return (
    <div className={`stat ${tone ? `is-${tone}` : ""}`}>
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
      {sub && (
        <span className={`stat-sub ${subTone ? `is-${subTone}` : ""}`}>{sub}</span>
      )}
    </div>
  );
}

const UNIT_LABEL = { icu: "ICU", trauma: "Trauma", cardiac: "Cardiac" };

const SEVERITY_CHIP = {
  critical: "chip chip-critical",
  urgent: "chip chip-warning",
  standard: "chip",
};

const STATUS_CHIP = {
  en_route: "chip chip-info",
  pending: "chip chip-warning",
  completed: "chip chip-good",
};

const STATUS_LABEL = {
  en_route: "En route",
  pending: "Pending",
  completed: "Completed",
};

export default function Dashboard({
  overview,
  hospitals,
  requests,
  requestMeta,
  requestScope,
  onRequestScopeChange,
  queue,
  unlocked,
  onUnlockChange,
  onUpdateBeds,
  onComplete,
}) {
  const [error, setError] = useState(null);
  const [draft, setDraft] = useState({});

  const run = async (fn) => {
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(err.message);
    }
  };

  // A skeleton rather than the word "Loading": it shows the shape of what is
  // coming, so the layout does not jump when the data lands.
  if (!overview) {
    return (
      <div className="dashboard" aria-busy="true" aria-live="polite">
        <span className="sr-only">Loading dashboard</span>
        <div className="stats">
          {Array.from({ length: 6 }, (_, i) => (
            <div className="stat" key={i}>
              <span className="skeleton skeleton-value" />
              <span className="skeleton skeleton-label" />
            </div>
          ))}
        </div>
        {Array.from({ length: 2 }, (_, i) => (
          <div className="panel" key={i}>
            <span className="skeleton skeleton-title" />
            {Array.from({ length: 4 }, (_, r) => (
              <span className="skeleton skeleton-row" key={r} />
            ))}
          </div>
        ))}
      </div>
    );
  }

  const { hospitals: h, ambulances: a, requests: r } = overview;

  const activeCount =
    (requestMeta?.byStatus?.pending ?? 0) + (requestMeta?.byStatus?.en_route ?? 0);

  // Beds are edited as a number, committed on blur or Enter. This replaced a
  // pair of increment buttons: typing 0 to close a hospital is one action
  // instead of eight clicks.
  const commitBeds = (hosp) => {
    const raw = draft[hosp.id];
    if (raw === undefined) return;
    const next = Number(raw);
    setDraft((d) => ({ ...d, [hosp.id]: undefined }));
    if (!Number.isFinite(next) || next === hosp.available_beds) return;
    run(() => onUpdateBeds(hosp.id, Math.max(0, Math.min(hosp.total_beds, next))));
  };

  return (
    <div className="dashboard">
      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
          <button
            type="button"
            className="banner-close"
            onClick={() => setError(null)}
            aria-label="Dismiss"
          >
            ✕
          </button>
        </div>
      )}

      <div className="admin-bar">
        <p className="note">
          {unlocked
            ? "Admin actions are enabled for this tab."
            : "Viewing is open to everyone. Changing capacity or completing a trip needs the admin key."}
        </p>
        <AdminLock unlocked={unlocked} onChange={onUnlockChange} />
      </div>

      <div className="stats">
        <Stat label="Beds free" value={h.available_beds} sub={`of ${h.total_beds}`} />
        <Stat
          label="Occupancy"
          value={`${h.occupancy_percent}%`}
          tone={h.occupancy_percent > 85 ? "critical" : undefined}
        />
        {/* The count of accepting hospitals is good news, so it stays neutral.
            The concern is the number that are FULL, so the tone goes there. */}
        <Stat
          label="Hospitals accepting"
          value={h.accepting_patients}
          sub={h.full > 0 ? `${h.full} full` : "none full"}
          subTone={h.full > 0 ? "warning" : undefined}
        />
        <Stat
          label="Ambulances free"
          value={a.available}
          sub={`of ${a.count}`}
          tone={a.available === 0 ? "critical" : undefined}
        />
        <Stat label="En route" value={r.en_route} />
        <Stat
          label="In triage queue"
          value={queue?.waiting ?? 0}
          tone={queue?.waiting > 0 ? "warning" : undefined}
        />
      </div>

      <div className="panel">
        <div className="panel-head">
          <h2>Hospital capacity</h2>
          <p className="note">
            Setting a hospital to zero free beds removes it from dispatch
            immediately. The ranking heap already filters on bed availability, so
            no routing code is involved.
          </p>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th className="col-grow">Hospital</th>
                <th className="numeric">Free beds</th>
                <th className="numeric">Total</th>
                <th className="numeric">Occupancy</th>
                <th>Units</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {hospitals.map((hosp) => (
                <tr key={hosp.id} className={hosp.accepting ? "" : "row-inactive"}>
                  <td className="col-grow">{hosp.name}</td>
                  <td className="numeric">
                    <input
                      className="bed-input"
                      type="number"
                      min="0"
                      max={hosp.total_beds}
                      value={draft[hosp.id] ?? hosp.available_beds}
                      disabled={!unlocked}
                      title={unlocked ? undefined : "Unlock admin to edit beds"}
                      onChange={(e) =>
                        setDraft((d) => ({ ...d, [hosp.id]: e.target.value }))
                      }
                      onBlur={() => commitBeds(hosp)}
                      onKeyDown={(e) => e.key === "Enter" && e.target.blur()}
                    />
                  </td>
                  <td className="numeric">{hosp.total_beds}</td>
                  <td className="numeric">{hosp.occupancy_percent}%</td>
                  <td>
                    {hosp.facilities?.length ? (
                      <span className="unit-list">
                        {hosp.facilities.map((f) => (
                          <span key={f} className="unit">
                            {UNIT_LABEL[f] || f}
                          </span>
                        ))}
                      </span>
                    ) : (
                      <span className="note">general only</span>
                    )}
                  </td>
                  <td>
                    <span className={hosp.accepting ? "chip chip-good" : "chip chip-critical"}>
                      {hosp.accepting ? "Accepting" : "Full"}
                    </span>
                  </td>
                  <td className="actions">
                    <div className="row-actions">
                    <button
                      className="secondary small"
                      onClick={() => run(() => onUpdateBeds(hosp.id, 0))}
                      disabled={!unlocked || !hosp.accepting}
                    >
                      Close
                    </button>
                    <button
                      className="secondary small"
                      onClick={() => run(() => onUpdateBeds(hosp.id, hosp.total_beds))}
                      disabled={!unlocked || hosp.available_beds >= hosp.total_beds}
                    >
                      Reopen
                    </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel">
        <div className="panel-head">
          <h2>
            Triage queue
            {queue?.waiting > 0 && <span className="badge">{queue.waiting}</span>}
          </h2>
          <p className="note">
            Patients waiting for an ambulance, in the order they will be served.
            The lowest score goes first. Severity sets the starting position, and
            every {queue?.aging_minutes_per_level ?? 10} minutes of waiting improves
            it by one full level, so no patient can be starved by a stream of more
            urgent arrivals.
          </p>
        </div>

        {queue?.queue?.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Position</th>
                  <th>Request</th>
                  {/* Absorbs the slack so Position and Request stay tight on
                      the left and the numeric columns stay tight on the right,
                      instead of all five drifting apart. */}
                  <th className="col-grow">Severity</th>
                  <th className="numeric">Waited</th>
                  <th className="numeric">Score</th>
                </tr>
              </thead>
              <tbody>
                {queue.queue.map((q) => (
                  <tr key={q.request_id}>
                    <td>{q.position}</td>
                    <td>{q.request_id}</td>
                    <td className="col-grow">
                      <span className={SEVERITY_CHIP[q.severity] || "chip"}>
                        {q.severity}
                      </span>
                    </td>
                    <td className="numeric">{q.waited_minutes} min</td>
                    <td className="numeric">{q.score.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="note">Nobody is waiting. Every request has an ambulance.</p>
        )}
      </div>

      <div className="panel">
        <div className="panel-head">
          <div className="head-row">
            <h2>Emergency requests</h2>
            {/* Completed trips are kept, not deleted: a finished request is the
                record of which hospital was chosen and why. They are just not
                what a dispatcher is looking at, so they are one click away
                rather than in the way. */}
            <div className="scope-toggle" role="group" aria-label="Which requests to show">
              <button
                type="button"
                className={requestScope === "active" ? "is-active" : ""}
                aria-pressed={requestScope === "active"}
                onClick={() => onRequestScopeChange("active")}
              >
                Live
                {activeCount > 0 && <span className="badge">{activeCount}</span>}
              </button>
              <button
                type="button"
                className={requestScope === "all" ? "is-active" : ""}
                aria-pressed={requestScope === "all"}
                onClick={() => onRequestScopeChange("all")}
              >
                All
              </button>
            </div>
          </div>
          <p className="note">
            Completing a trip frees the ambulance and parks it at the hospital, so
            the next dispatch measures from where it actually is.
            {requestMeta?.byStatus && (
              <>
                {" "}
                {requestMeta.byStatus.completed} completed so far, kept as a
                record rather than deleted.
              </>
            )}
          </p>
        </div>

        {requestMeta?.truncated && (
          <p className="note">
            Showing the {requests.length} most recent of {requestMeta.matched}.
          </p>
        )}

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Request</th>
                <th>Status</th>
                <th>Severity</th>
                <th className="col-grow">Hospital</th>
                <th>Ambulance</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((req) => (
                <tr key={req.id}>
                  <td>{req.id}</td>
                  <td>
                    <span className={STATUS_CHIP[req.status] || "chip"}>
                      {STATUS_LABEL[req.status] || req.status}
                    </span>
                  </td>
                  <td>
                    <span className={SEVERITY_CHIP[req.severity] || "chip"}>
                      {req.severity}
                    </span>
                  </td>
                  <td className="col-grow">{req.assigned_hospital_name || "Not assigned"}</td>
                  <td>{req.assigned_ambulance_id ?? "None"}</td>
                  <td className="actions">
                    <div className="row-actions">
                    {req.status !== "completed" && (
                      <button
                        className="secondary small"
                        onClick={() => run(() => onComplete(req.id))}
                        disabled={!unlocked}
                        title={unlocked ? undefined : "Unlock admin to complete a trip"}
                      >
                        Complete
                      </button>
                    )}
                    </div>
                  </td>
                </tr>
              ))}
              {requests.length === 0 && (
                <tr className="empty-row">
                  <td colSpan="6">
                    {requestScope === "active"
                      ? "Nothing live right now. Every request has been completed."
                      : "No requests yet."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
