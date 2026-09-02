import { useEffect, useRef, useState } from "react";
import {
  searchAddress,
  reverseGeocode,
  currentPosition,
  isInsideCoverage,
} from "../api/geocode";

/**
 * Severity in the words a caller would use, not the words a database uses.
 *
 * "critical" means nothing on its own; "unconscious or not breathing" is
 * something a person can actually match against what is in front of them. The
 * stored value is unchanged, so the triage queue and its scoring are
 * untouched: this is a labelling change, not a model change.
 */
const SEVERITY = [
  {
    value: "critical",
    title: "Critical",
    hint: "Unconscious, not breathing, severe bleeding",
  },
  {
    value: "urgent",
    title: "Urgent",
    hint: "Conscious but in serious pain or distress",
  },
  {
    value: "standard",
    title: "Standard",
    hint: "Stable, needs transport but not immediately at risk",
  },
];

const DEMO = { lat: 28.4746, lng: 77.0518 };

export default function RequestForm({ patient, onPickPatient, onSubmit, busy }) {
  const [severity, setSeverity] = useState("standard");
  const [error, setError] = useState(null);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [locating, setLocating] = useState(false);
  // The human readable address for whatever is currently pinned.
  const [address, setAddress] = useState(null);

  // Set when a location was chosen here, so the reverse geocode below can skip
  // work it already has the answer for.
  const knownLabel = useRef(null);

  // Debounced address search. Nominatim asks for at most one request per
  // second, and a request per keystroke would breach that immediately, so
  // typing settles for 500ms first. The in-flight request is aborted when the
  // query changes, which also stops an older slower response overwriting a
  // newer one.
  useEffect(() => {
    if (query.trim().length < 3) {
      setResults([]);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        setResults(await searchAddress(query, { signal: controller.signal }));
        setError(null);
      } catch (err) {
        if (err.name !== "AbortError") setError(err.message);
      } finally {
        setSearching(false);
      }
    }, 500);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  // Name whatever is pinned, however it got pinned: a click on the map, the
  // demo button, or the device. Without this, clicking the map would leave the
  // panel showing coordinates again, which is the thing this replaced.
  useEffect(() => {
    if (!patient) {
      setAddress(null);
      return;
    }
    if (knownLabel.current) {
      setAddress(knownLabel.current);
      knownLabel.current = null;
      return;
    }
    const controller = new AbortController();
    setAddress(null);
    reverseGeocode(patient.lat, patient.lng, { signal: controller.signal })
      .then((label) => label && setAddress(label))
      .catch(() => {
        /* A missing label is cosmetic. The coordinates still dispatch. */
      });
    return () => controller.abort();
  }, [patient]);

  const choose = (lat, lng, label) => {
    knownLabel.current = label ?? null;
    onPickPatient(lat, lng);
    setQuery("");
    setResults([]);
    setError(null);
  };

  const useMyLocation = async () => {
    setLocating(true);
    setError(null);
    try {
      const { lat, lng } = await currentPosition();
      if (!isInsideCoverage(lat, lng)) {
        setError(
          "You are outside the area this demo has road data for. It covers part of Gurugram only. Use the example location to try it."
        );
        return;
      }
      choose(lat, lng, null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLocating(false);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!patient) {
      setError("Set the patient's location first.");
      return;
    }
    try {
      // The facility argument stays in the API and is sent as null. The
      // picker was removed because a caller cannot reasonably know which
      // specialist unit is needed; the backend filter still works and is
      // exercised through the API and the Board's Units column.
      await onSubmit(patient.lat, patient.lng, severity, null);
    } catch (err) {
      setError(err.message);
    }
  };

  const outside = patient && !isInsideCoverage(patient.lat, patient.lng);

  return (
    <form className="panel" onSubmit={submit}>
      <div className="panel-head">
        <h2>New emergency request</h2>
        <p className="note">
          Say where the patient is, how urgent it is, then dispatch.
        </p>
      </div>

      <div className="field">
        <label htmlFor="address">Where is the patient?</label>
        <div className="search-row">
          <input
            id="address"
            type="search"
            placeholder="Search an address or landmark"
            value={query}
            autoComplete="off"
            onChange={(e) => setQuery(e.target.value)}
          />
          <button
            type="button"
            className="secondary"
            onClick={useMyLocation}
            disabled={locating}
          >
            {locating ? "Locating" : "Use my location"}
          </button>
        </div>

        {searching && <p className="note">Searching</p>}

        {results.length > 0 && (
          <ul className="search-results">
            {results.map((r) => (
              <li key={r.id}>
                <button type="button" onClick={() => choose(r.lat, r.lng, r.label)}>
                  {r.label}
                </button>
              </li>
            ))}
          </ul>
        )}

        {query.trim().length >= 3 && !searching && results.length === 0 && (
          <p className="note">
            Nothing found inside the covered area. Try a nearby landmark, or
            click straight on the map.
          </p>
        )}
      </div>

      {/* What is currently pinned, in words first and coordinates second. The
          coordinates stay visible because they are what actually gets sent,
          and hiding them would make the demo harder to reason about. */}
      <div className={`pinned ${patient ? "is-set" : ""}`}>
        {patient ? (
          <>
            <span className="pinned-label">Patient location</span>
            <strong>{address || "Naming this place"}</strong>
            <span className="pinned-coords">
              {patient.lat.toFixed(4)}, {patient.lng.toFixed(4)}
            </span>
            {outside && (
              <span className="pinned-warn">
                Outside the mapped road network. Dispatch will snap to the
                nearest junction it knows, which may be far away.
              </span>
            )}
          </>
        ) : (
          <>
            <span className="pinned-label">No location set</span>
            <span className="note">
              Search above, use your location, or click anywhere on the map.
            </span>
          </>
        )}
      </div>

      <fieldset className="severity">
        <legend>How urgent is it?</legend>
        {SEVERITY.map((s) => (
          <label
            key={s.value}
            className={`severity-option ${severity === s.value ? "is-active" : ""}`}
          >
            <input
              type="radio"
              name="severity"
              value={s.value}
              checked={severity === s.value}
              onChange={() => setSeverity(s.value)}
            />
            <span>
              <strong>{s.title}</strong>
              <span className="sub">{s.hint}</span>
            </span>
          </label>
        ))}
      </fieldset>

      {error && <p className="warn-text">{error}</p>}

      <div className="form-actions">
        <button type="submit" disabled={busy || !patient}>
          {busy ? "Dispatching" : "Dispatch ambulance"}
        </button>
        <button
          type="button"
          className="secondary"
          onClick={() => choose(DEMO.lat, DEMO.lng, null)}
        >
          Use example location
        </button>
      </div>
    </form>
  );
}
