import { useState } from "react";

const FACILITIES = [
  { value: "", label: "None needed (general case)" },
  { value: "icu", label: "Intensive care" },
  { value: "trauma", label: "Trauma unit" },
  { value: "cardiac", label: "Cardiac unit" },
];

const SEVERITIES = [
  { value: "critical", label: "Critical (life threatening)" },
  { value: "urgent", label: "Urgent (serious, not immediately fatal)" },
  { value: "standard", label: "Standard (stable)" },
];

export default function RequestForm({ patient, onPickPatient, onSubmit, busy }) {
  const [error, setError] = useState(null);
  const [severity, setSeverity] = useState("standard");
  const [facility, setFacility] = useState("");

  // The seeded road grid spans 28.44 to 28.50 lat and 77.00 to 77.06 lng.
  // Outside that the nearest road node is far away and the route looks
  // nonsensical, so this gives a known good starting point.
  const usePreset = () => onPickPatient(28.44, 77.0);

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!patient) {
      setError("Choose a location on the map first, or use the demo location.");
      return;
    }
    try {
      await onSubmit(patient.lat, patient.lng, severity, facility || null);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <form className="panel" onSubmit={submit}>
      <div className="panel-head">
        <h2>New emergency request</h2>
        <p className="note">
          Set the patient location and triage severity, then dispatch.
        </p>
      </div>

      <div className="field-row">
        <label>
          Latitude
          <input
            type="number"
            step="0.0001"
            placeholder="28.4400"
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
            placeholder="77.0000"
            value={patient?.lng ?? ""}
            onChange={(e) =>
              onPickPatient(patient?.lat ?? 28.44, parseFloat(e.target.value))
            }
          />
        </label>
      </div>

      <div className="field-row">
        <label>
          Severity
          <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
            {SEVERITIES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="field-row">
        <label>
          Required unit
          <select value={facility} onChange={(e) => setFacility(e.target.value)}>
            {FACILITIES.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="actions-row">
        <button type="submit" disabled={busy}>
          {busy ? "Dispatching" : "Create request"}
        </button>
        <button type="button" className="secondary" onClick={usePreset}>
          Use demo location
        </button>
      </div>

      {error && <p className="error">{error}</p>}
    </form>
  );
}
