import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import MapView from "./components/MapView";
import RequestForm from "./components/RequestForm";
import ResultsPanel from "./components/ResultsPanel";
import Dashboard from "./components/Dashboard";

const LIVE_POLL_MS = 2000;

export default function App() {
  const [tab, setTab] = useState("map");
  const [patient, setPatient] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  const [hospitals, setHospitals] = useState([]);
  const [requests, setRequests] = useState([]);
  const [overview, setOverview] = useState(null);
  const [queue, setQueue] = useState(null);
  const [live, setLive] = useState([]);
  const [connError, setConnError] = useState(null);

  // Everything the dashboard and map need, refreshed together so the two tabs
  // never disagree about the state of the world.
  const refresh = useCallback(async () => {
    try {
      const [h, r, o, q] = await Promise.all([
        api.listHospitals(),
        api.listRequests(),
        api.overview(),
        api.queue(),
      ]);
      setHospitals(h.hospitals);
      setRequests(r.requests);
      setOverview(o);
      setQueue(q);
      setConnError(null);
    } catch (err) {
      setConnError(err.message);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // The live tracking loop. Ambulance positions are computed server-side from
  // elapsed time, so simply asking again gives an updated position -- there is
  // no client-side animation state to keep in sync.
  useEffect(() => {
    let cancelled = false;

    const tick = async () => {
      try {
        const data = await api.liveAmbulances();
        if (!cancelled) {
          setLive(data.ambulances);
          setConnError(null);
        }
      } catch (err) {
        if (!cancelled) setConnError(err.message);
      }
    };

    tick();
    const id = setInterval(tick, LIVE_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const pickPatient = (lat, lng) => {
    if (Number.isFinite(lat) && Number.isFinite(lng)) setPatient({ lat, lng });
  };

  const createRequest = async (lat, lng, severity) => {
    setBusy(true);
    try {
      const created = await api.createRequest(lat, lng, severity);
      setResult(created);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const updateBeds = async (id, beds) => {
    await api.updateBeds(id, beds);
    await refresh();
  };

  const completeRequest = async (id) => {
    await api.completeRequest(id);
    await refresh();
  };

  const movingCount = live.filter((a) => a.request_id !== null).length;

  return (
    <div className="app">
      <header>
        <div>
          <h1>Ambulance Route Optimizer</h1>
          <p className="subtitle">
            Simulated data — a portfolio demonstration, not a medically validated
            system.
          </p>
        </div>
        <nav>
          <button
            className={tab === "map" ? "active" : ""}
            onClick={() => setTab("map")}
          >
            Map {movingCount > 0 && <span className="badge">{movingCount}</span>}
          </button>
          <button
            className={tab === "dashboard" ? "active" : ""}
            onClick={() => setTab("dashboard")}
          >
            Dashboard
          </button>
        </nav>
      </header>

      {connError && (
        <p className="error banner">
          Cannot reach the API at localhost:8001 — {connError}. Is the backend
          running (<code>uvicorn app.main:app --reload --port 8001</code>)?
        </p>
      )}

      {tab === "map" ? (
        <div className="layout">
          <MapView
            hospitals={hospitals}
            live={live}
            patient={patient}
            onPickPatient={pickPatient}
          />
          <aside>
            <RequestForm
              patient={patient}
              onPickPatient={pickPatient}
              onSubmit={createRequest}
              busy={busy}
            />
            <ResultsPanel result={result} />
          </aside>
        </div>
      ) : (
        <Dashboard
          overview={overview}
          hospitals={hospitals}
          requests={requests}
          queue={queue}
          onUpdateBeds={updateBeds}
          onComplete={completeRequest}
        />
      )}
    </div>
  );
}
