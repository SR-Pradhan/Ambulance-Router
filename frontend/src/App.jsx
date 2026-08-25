import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import MapView from "./components/MapView";
import RequestForm from "./components/RequestForm";
import ResultsPanel from "./components/ResultsPanel";
import Dashboard from "./components/Dashboard";
import ThemeToggle from "./components/ThemeToggle";

const LIVE_POLL_MS = 2000;
const THEME_KEY = "theme";

function readStoredTheme() {
  try {
    const saved = localStorage.getItem(THEME_KEY);
    return saved === "light" || saved === "dark" ? saved : null;
  } catch {
    // Storage can throw in private mode or when site data is blocked. Falling
    // back to the system setting is the right behaviour, not an error.
    return null;
  }
}

/**
 * Theme state. `theme` is the user's explicit choice, or null meaning follow
 * the system. `resolved` is what is actually on screen, which is what the rest
 * of the UI needs to know.
 */
function useTheme() {
  const [theme, setTheme] = useState(readStoredTheme);
  const [systemDark, setSystemDark] = useState(
    () => window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false
  );

  // Track the OS setting so "System" updates live rather than only on reload.
  useEffect(() => {
    const mq = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (!mq) return;
    const onChange = (e) => setSystemDark(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (theme) root.dataset.theme = theme;
    else delete root.dataset.theme;

    try {
      if (theme) localStorage.setItem(THEME_KEY, theme);
      else localStorage.removeItem(THEME_KEY);
    } catch {
      // Not being able to remember the choice is not worth breaking the app.
    }
  }, [theme]);

  const resolved = theme ?? (systemDark ? "dark" : "light");
  return { theme, resolved, setTheme };
}

export default function App() {
  const { theme, resolved, setTheme } = useTheme();
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
            Simulated data. A portfolio demonstration, not a medically validated
            system.
          </p>
        </div>
        <div className="header-controls">
          <ThemeToggle theme={theme} resolved={resolved} onChange={setTheme} />
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
        </div>
      </header>

      {connError && (
        <p className="error-banner">
          Cannot reach the API at localhost:8001. {connError}. Check the backend is
          running with <code>uvicorn app.main:app --reload --port 8001</code>
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
