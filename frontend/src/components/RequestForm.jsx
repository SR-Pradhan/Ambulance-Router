import { useState } from "react";

const SEVERITIES = [
  { value: "critical", label: "Critical", hint: "life-threatening" },
  { value: "urgent", label: "Urgent", hint: "serious, not immediately fatal" },
  { value: "standard", label: "Standard", hint: "stable" },
];

export default function RequestForm({ patient, onPickPatient, onSubmit, busy }) {
  const [error, setError] = useState(null);
  const [severity, setSeverity] = useState("standard");

  // The seeded road grid spans 28.44-28.50 lat, 77.00-77.06 lng. Outside that
  // the nearest road node is far away and the route looks nonsensical, so this
  // gives someone a known-good starting point.
  const usePreset = () => onPickPatient(28.44, 77.0);

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!patient) {
      setError("Pick a location on the map first.");
      return;
    }
    try {
      await onSubmit(patient.lat, patient.lng, severity);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <form className="panel" onSubmit={submit}>
      <h2>New emergency request</h2>

      <div className="row">
        <label>
          Latitude
          <input
            type="number"
            step="0.0001"
            value={patient?.lat ?? ""}
            onChange={(e) =>
              onPickPatient(parseFloat(e.target.value), patient?.lng ?? 77.0)
            }
          />
        </label>
        <label>
          Longitude
          <input
            type="number"
            step="0.0001"
            value={patient?.lng ?? ""}
            onChange={(e) =>
              onPickPatient(patient?.lat ?? 28.44, parseFloat(e.target.value))
            }
          />
        </label>
      </div>

      <div className="row">
        <label>
          Severity
          <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
            {SEVERITIES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label} — {s.hint}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="row">
        <button type="submit" disabled={busy}>
          {busy ? "Dispatching…" : "Create request"}
        </button>
        <button type="button" className="secondary" onClick={usePreset}>
          Use demo location
        </button>
      </div>

      {error && <p className="error">{error}</p>}
    </form>
  );
}
