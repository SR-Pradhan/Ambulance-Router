# 🚑 Emergency Ambulance Route Optimizer

**[▶️ Live demo](https://ambulance-router.vercel.app)** · [📖 Deployment guide](DEPLOYMENT.md)

A full-stack dispatch system that takes a patient's location and answers two questions:
**which hospital should they go to**, and **what is the fastest road route there** —
then dispatches the nearest available ambulance and tracks it on a live map.

> ⚠️ **All capacity and traffic data in this project is simulated.** The road network
> and hospital names are real OpenStreetMap data, but bed counts, specialist units,
> congestion figures and ambulance positions are invented. This is a portfolio
> demonstration of algorithms and system design. **It is not a medically validated
> system and must not be used as one.**

---

## ✨ What makes it interesting

🧮 **The routing algorithms are hand-written.** Dijkstra, A\*, the min-heap ranking
and the triage priority queue are all implemented from scratch — no `networkx`, no
shortest-path library.

⚡ **A\* is measurably faster, and provably correct.** `/route?algo=compare` runs both
and reports node expansions: on the real 433-junction network Dijkstra expands **379**
nodes and A\* expands **286**, for the same route.

🚦 **Traffic changes the road taken, not just the ETA.** Edge weights are travel
**time**, so a congested shortcut loses to a clear detour. On the demo grid a 3.9 km
direct route is rejected in favour of an 8.4 km one that is genuinely faster.

🏥 **Ranking balances distance against capacity.** A hospital with no spare beds is
ranked as if it were 3 minutes further away — enough to break ties, never enough to
send a patient past a much closer hospital.

⏱️ **Triage that cannot starve anyone.** Severity sets your place in the queue, and
every 10 minutes of waiting improves it by one full level, so a routine case behind a
stream of critical arrivals still gets served.

📍 **Live tracking with no background jobs.** An ambulance's position is derived from
elapsed time along its computed route, so it is consistent on every request and
survives a restart. No GPS is involved and none is claimed.

🎨 **Built to be read.** An operations console shell (fixed rail, live figures in the top bar, one scrolling work area), light and dark themes, a map legend, skeleton loading
states, and WCAG AA contrast throughout. No status is signalled by colour alone.

---

## 🛠️ Stack

| Layer | Choice |
|---|---|
| 🐍 Backend | Python + FastAPI |
| 🧮 Algorithms | Hand-written Dijkstra, A\*, min-heap, binary heap |
| 🐘 Database | PostgreSQL + SQLAlchemy |
| ⚛️ Frontend | React + Leaflet (Vite) |
| 🗺️ Map data | OpenStreetMap via Overpass |

---

## 🚀 Running it locally

### 1️⃣ Backend and database

```bash
createdb ambulance_router

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python seed_data.py

export ADMIN_KEY=local-dev-key
uvicorn app.main:app --reload --port 8001
```

> 🔐 `ADMIN_KEY` gates the two destructive endpoints. **Without it they return
> 503** — the check fails closed on purpose, so a missing key is loud rather
> than silently leaving them open. Any value works locally; you type the same
> one into the dashboard's **Unlock admin** button.

`seed_data.py` creates the tables from the SQLAlchemy models, then seeds the **real
Gurugram road network** from cached OpenStreetMap data in `backend/data/` (540 KB,
committed, so no internet needed). Add `--synthetic` to rebuild the original 4×4
invented grid instead.

> 💡 Verified end to end on an empty database and in a clean virtualenv: these
> commands are the complete setup, with nothing to run by hand in `psql`.

📚 Interactive API docs: <http://localhost:8001/docs>

### 2️⃣ Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens on <http://localhost:5174>.

### 3️⃣ Tests

```bash
cd backend
python tests/test_dijkstra.py       # 9
python tests/test_astar.py          # 8
python tests/test_heap_ranking.py   # 16
python tests/test_geo.py            # 14
python tests/test_priority_queue.py # 12
python tests/test_facilities.py     # 6
python tests/test_traffic.py        # 9
python tests/test_osm.py            # 8
python tests/test_auth.py           # 7   → 89 total
```

✅ The algorithm tests use hand-built graphs and need no database or server — that is
the point of keeping `app/dsa/` free of any framework imports.

---

## 🔌 API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/route?source=&dest=&algo=&hour=` | Fastest route. `algo=dijkstra\|astar\|compare` |
| `GET` | `/hospitals/nearby?lat=&lng=&top_k=` | Rank hospitals by straight-line distance |
| `GET` | `/hospitals` | All hospitals with capacity and units |
| `PATCH` | `/hospitals/{id}/beds` | 🔐 Update available beds |
| `POST` | `/requests` | Create an emergency request and dispatch |
| `GET` | `/requests` | List all requests |
| `GET` | `/requests/{id}` | One request with its route |
| `PATCH` | `/requests/{id}/complete` | 🔐 Finish a trip, free the ambulance |
| `GET` | `/queue` | Triage queue, in service order |
| `GET` | `/ambulances` | All ambulances |
| `GET` | `/ambulances/live` | Simulated live positions |
| `GET` | `/admin/overview` | Dashboard statistics |

🔐 marks the two endpoints requiring the `X-Admin-Key` header. Everything else,
including creating a request, is public so the live demo works for visitors.

---

## 📁 Project layout

```
backend/
  app/
    dsa/          🧮 Pure algorithms. No FastAPI, no database, fully testable alone
      graph.py         adjacency list
      dijkstra.py      shortest path + all-targets variant
      astar.py         informed search, admissible heuristic
      heap_ranking.py  hospital ranking by distance and capacity
      priority_queue.py hand-written binary heap for triage
      geo.py           haversine, snapping, path interpolation
      traffic.py       congestion model, distance to travel time
    api/          🔌 Thin FastAPI routers: fetch data, call dsa/, format JSON
      deps.py          shared dependencies, including the admin guard
    models/       🗃️ SQLAlchemy ORM models
    schemas/      ✅ Pydantic request and response validation
    facilities.py 🏥 Hospital capability matching
    auth.py       🔐 Admin key comparison (framework free, so it tests alone)
    osm.py        🗺️ OpenStreetMap parsing and graph simplification
    graph_loader.py  shared road-network loading
  data/           💾 Cached OpenStreetMap responses (540 KB)
  osm_seed.py     Overpass fetch, caching, hospital selection
  seed_data.py    Creates the schema and seeds the road network
  migrate.py      Idempotent ALTER TABLEs, run on every deploy
  tests/          🧪 89 tests

frontend/src/
  api/client.js   Every backend call lives here
  components/
    MapView.jsx      🗺️ Leaflet map, live ambulances, routes
    RequestForm.jsx  📝 Create an emergency request
    ResultsPanel.jsx 📊 Chosen hospital, route, ETA
    Dashboard.jsx    🎛️ Capacity management, triage queue, requests
    AdminLock.jsx    🔐 Unlock control for the gated actions
    ThemeToggle.jsx  🌓 Light, dark and system themes
```

The `dsa/` ↔ `api/` split is the central design decision: **algorithms never import
the web framework or the database**, so they can be tested in isolation and would
survive swapping either one out.

---

## 🧭 How it works

A single dispatch, end to end:

1. 📍 **Snap** the patient's coordinates to the nearest road junction
2. 🔍 **One Dijkstra run** gives the travel time to every junction, and therefore to
   every hospital *and* every ambulance — the graph is undirected, so one search
   answers both
3. 🏥 **Filter** hospitals with no free beds, and any lacking a required specialist unit
4. ⚖️ **Rank** the survivors on travel time plus a capacity penalty, using a min-heap
5. 🛣️ **Reconstruct** the road route to the winner
6. 🚑 **Dispatch** the nearest free ambulance, or queue the patient by triage score
7. ⏱️ **Track** its position, interpolated from elapsed time along the route

---

## ⚠️ Known simplifications

Stated deliberately rather than hidden:

- 🗺️ **Roads and hospital names are real; capacity and traffic are not.** The network
  (433 junctions, 643 segments) and the 12 hospital names come from OpenStreetMap.
  Bed counts, specialist units, congestion figures and ambulance positions are invented.
- 🚦 Congestion is derived from road class and time of day, not measured.
- 📌 Only arterial roads are in the graph, so a patient snaps to a junction that
  can be a few hundred metres from the actual pin. The map draws that last
  stretch as a dashed line labelled "not routed" rather than pretending to
  cover it.
- 📡 Live positions are interpolated from elapsed time since dispatch, not GPS. Trips auto-complete on arrival, so `/ambulances/live` writes state: a deliberate trade to avoid running a background worker.
- 🔒 Admin actions (changing beds, completing a trip) are gated by a single
  shared key, not real accounts. It proves a request was *authorised*, not *who*
  made it, and there is no audit trail. Viewing stays public.
- 🔁 Ambulance dispatch has no locking; concurrent requests could race.
- 🗄️ No real migration tool. `migrate.py` is an idempotent list of `ALTER TABLE` statements run at deploy time, which is enough here but would not scale to a schema with data to preserve. Alembic is the correct answer beyond this.
- 🛤️ All roads are two-way; one-way streets are not modelled.

---

## 📄 Licence

Portfolio project. Map data © OpenStreetMap contributors.
