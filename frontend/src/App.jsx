import { useCallback, useEffect, useState } from "react";
import { api, adminKey } from "./api/client";
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
  // Whether this tab holds an admin key. The SERVER decides if it is valid;
  // this only controls whether the buttons are offered.
  const [unlocked, setUnlocked] = useState(() => Boolean(adminKey.get()));
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

    // Only poll while the tab is actually visible.
    //
    // This matters more than it looks. A forgotten open tab polling every two
    // seconds keeps a free-tier backend permanently awake, and on Render the
    // free instance-hours are shared across the whole workspace: one abandoned
    // tab could exhaust the monthly pool and suspend every other free service
    // on the account. Pausing on hide costs nothing and removes that risk.
    let id = null;

    const start = () => {
      if (id === null) {
        tick();
        id = setInterval(tick, LIVE_POLL_MS);
      }
    };

    const stop = () => {
      if (id !== null) {
        clearInterval(id);
        id = null;
      }
    };

    const onVisibility = () => {
      if (document.visibilityState === "visible") start();
      else stop();
    };

    onVisibility();
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      cancelled = true;
      stop();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  const pickPatient = (lat, lng) => {
    if (Number.isFinite(lat) && Number.isFinite(lng)) setPatient({ lat, lng });
  };

  const createRequest = async (lat, lng, severity, requiredFacility) => {
    setBusy(true);
    try {
      const created = await api.createRequest(lat, lng, severity, requiredFacility);
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

  // The figures worth having on screen at all times, including while you are
  // looking at the map rather than the dashboard.
  const pills = overview
    ? [
        { label: "beds free", value: overview.hospitals.available_beds },
        {
          label: "units free",
          value: overview.ambulances.available,
          tone: overview.ambulances.available === 0 ? "critical" : null,
        },
        { label: "en route", value: overview.requests.en_route },
        {
          label: "in queue",
          value: queue?.waiting ?? 0,
          tone: queue?.waiting > 0 ? "warning" : null,
        },
      ]
    : [];

  return (
    <div className="shell">
      <nav className="rail" aria-label="Views">
        <span className="rail-mark" aria-hidden="true">🚑</span>

        <button
          type="button"
          className={`rail-btn ${tab === "map" ? "is-active" : ""}`}
          aria-current={tab === "map" ? "page" : undefined}
          onClick={() => setTab("map")}
        >
          <span className="rail-icon" aria-hidden="true">🗺️</span>
          Map
          {movingCount > 0 && (
            <span className="rail-badge">
              {movingCount}
              <span className="sr-only"> ambulances moving</span>
            </span>
          )}
        </button>

        <button
          type="button"
          className={`rail-btn ${tab === "dashboard" ? "is-active" : ""}`}
          aria-current={tab === "dashboard" ? "page" : undefined}
          onClick={() => setTab("dashboard")}
        >
          <span className="rail-icon" aria-hidden="true">📊</span>
          Board
        </button>

        <span className="rail-spacer" />
      </nav>

      <div className="workspace">
        <header className="topbar">
          <div>
            <h1>Ambulance Route Optimizer</h1>
            <p className="subtitle">
              Simulated data. Not a medically validated system.
            </p>
          </div>

          <div className="topbar-live">
            {pills.map((p) => (
              <span
                key={p.label}
                className={`live-pill ${p.tone ? `is-${p.tone}` : ""}`}
              >
                <b>{p.value}</b> {p.label}
              </span>
            ))}
            <ThemeToggle theme={theme} resolved={resolved} onChange={setTheme} />
          </div>
        </header>

        <main className={`workarea ${tab === "map" ? "is-map" : "is-board"}`}>
          {connError && (
            <p className="error-banner">
              Cannot reach the API. {connError}. If you are running locally,
              check the backend is started with{" "}
              <code>uvicorn app.main:app --reload --port 8001</code>
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
              unlocked={unlocked}
              onUnlockChange={setUnlocked}
              onUpdateBeds={updateBeds}
              onComplete={completeRequest}
            />
          )}
        </main>
      </div>
    </div>
  );
}
