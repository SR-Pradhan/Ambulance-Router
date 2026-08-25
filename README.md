# Emergency Ambulance Route Optimizer

A full-stack system that takes a patient's location and answers two questions:
**which hospital should they go to**, and **what is the fastest road route there** —
then dispatches the nearest available ambulance and tracks it on a live map.

> **All data in this project is simulated.** Locations, road network, hospitals and
> ambulances are synthetic. This is a portfolio demonstration of algorithms and
> system design. **It is not a medically validated system and must not be used as
> one.**

---

## What makes it interesting

- **The routing algorithms are hand-written.** Dijkstra, A\* and the min-heap
  ranking are implemented from scratch — no `networkx`, no shortest-path library.
- **A\* is measurably faster, and provably correct.** `/route?algo=compare` runs
  both and reports node expansions: 15 for Dijkstra vs 9 for A\* on the seeded
  grid, same distance.
- **Ranking on road distance changes the answer.** Straight-line distance picks
  City Hospital (3.068 km); routing through the actual road network shows
  Sunrise Medical is genuinely closer (3.912 km vs 4.179 km by road).
- **Live tracking with no background jobs.** An ambulance's position is derived
  from elapsed time along its computed route, so it is consistent on every
  request and survives a restart.

---

## Stack

| Layer | Choice |
|---|---|
| Backend | Python + FastAPI |
| Algorithms | Hand-written Dijkstra, A\*, min-heap |
| Database | PostgreSQL + SQLAlchemy |
| Frontend | React + Leaflet (Vite) |

---

## Running it

**Ports:** the backend runs on **8001** and the frontend on **5174** — not the
usual 8000/5173, which are taken by other services on the development machine.
If you change them, update `frontend/src/api/client.js` and `ALLOWED_ORIGINS`
in `backend/app/main.py` together, or the browser will block every request.

### 1. Backend and database

```bash
createdb ambulance_router          # first time only

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python seed_data.py                # creates the tables AND seeds demo data
uvicorn app.main:app --reload --port 8001
```

`seed_data.py` creates any missing tables from the SQLAlchemy models before
seeding, so an empty database is all it needs. It is **destructive and
idempotent**: it truncates every table and rebuilds, so running it twice gives
the same result — including wiping any emergency requests made through the API.

> Verified end to end on an empty database and in a clean virtualenv: the
> commands above are the complete setup, with nothing to run by hand in `psql`.

**Schema changes:** `create_all()` creates missing *tables* but never alters
existing ones. If you add a column to a model, an already-created table will not
gain it — this project has no migration tool (no Alembic), so either drop and
recreate the database or `ALTER TABLE` by hand.

Interactive API docs: <http://localhost:8001/docs>

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5174
```

### 3. Tests

```bash
cd backend
python tests/test_dijkstra.py      # 9
python tests/test_astar.py         # 6
python tests/test_heap_ranking.py  # 10
python tests/test_geo.py           # 14
python tests/test_priority_queue.py # 12  -> 51 total
```

The algorithm tests use hand-built graphs and need no database or server —
that is the point of keeping `app/dsa/` free of any framework imports.

---

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/route?source=&dest=&algo=` | Shortest path. `algo=dijkstra\|astar\|compare` |
| `GET` | `/hospitals/nearby?lat=&lng=&top_k=` | Rank hospitals by straight-line distance |
| `GET` | `/hospitals` | All hospitals with capacity |
| `PATCH` | `/hospitals/{id}/beds` | Update available beds |
| `POST` | `/requests` | Create an emergency request (dispatch) |
| `GET` | `/requests` | List all requests |
| `GET` | `/requests/{id}` | One request with its route |
| `PATCH` | `/requests/{id}/complete` | Finish a trip, free the ambulance |
| `GET` | `/ambulances` | All ambulances |
| `GET` | `/ambulances/live` | Simulated live positions |
| `GET` | `/admin/overview` | Dashboard statistics |
| `GET` | `/queue` | Triage queue, in service order |

---

## Project layout

```
backend/
  app/
    dsa/        Pure algorithms - no FastAPI, no database, fully testable alone
    api/        Thin FastAPI routers: fetch data, call dsa/, format JSON
    models/     SQLAlchemy ORM models
    schemas/    Pydantic request/response validation
    graph_loader.py   Shared road-network loading
  tests/        51 algorithm tests
  seed_data.py  Creates the schema + rebuilds the simulated road network

frontend/
  src/
    api/client.js       Every backend call lives here
    components/
      MapView.jsx       Leaflet map, live ambulances, routes
      RequestForm.jsx   Create an emergency request
      ResultsPanel.jsx  Chosen hospital, route, ETA
      Dashboard.jsx     Capacity management and request list
```

The `dsa/` ↔ `api/` split is the central design decision: algorithms never import
the web framework or the database, so they can be tested in isolation and would
survive swapping either one out.

---

## Known simplifications

Stated deliberately rather than hidden:

- **The road network is synthetic, but the map tiles are real.** The 16 nodes sit
  on a perfect 0.02° lattice over Gurugram, so every "road" is a ruler-straight
  line between grid points and drawn routes visibly cross real buildings. The
  algorithms are genuine and the answers are correct *for this simulated city* —
  they are not navigable directions for the real one. Importing real
  OpenStreetMap road data would fix this without changing any algorithm.
- ETA assumes a constant 40 km/h with no traffic model.
- Live positions are interpolated from elapsed time, not GPS.
- Ambulance dispatch has no locking; concurrent requests could race.
- The computed route is not persisted, so it is recomputed on read.
- Triage uses a fixed aging rate (10 min per severity level) rather than a
  clinically derived one.
- No database migrations — schema changes need a manual `ALTER TABLE`.
