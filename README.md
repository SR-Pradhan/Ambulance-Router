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

### 1. Database

```bash
createdb ambulance_router          # first time only
cd backend
python seed_data.py                # builds the road network and demo data
```

`seed_data.py` is **destructive and idempotent**: it truncates every table and
rebuilds, so running it twice gives the same result. It also wipes any emergency
requests created through the API.

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Interactive API docs: <http://localhost:8001/docs>

### 3. Frontend

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5174
```

### 4. Tests

```bash
cd backend
python tests/test_dijkstra.py      # 9
python tests/test_astar.py         # 6
python tests/test_heap_ranking.py  # 10
python tests/test_geo.py           # 14   -> 39 total
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
  tests/        39 algorithm tests
  seed_data.py  Rebuilds the simulated road network and demo data

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

- Simulated coordinates and a synthetic 4×4 road grid — no real map data.
- ETA assumes a constant 40 km/h with no traffic model.
- Live positions are interpolated from elapsed time, not GPS.
- Ambulance dispatch has no locking; concurrent requests could race.
- The computed route is not persisted, so it is recomputed on read.
- No triage priority queue yet — requests are handled first-come, first-served.
