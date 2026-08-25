"""Seed the ambulance_router database with a simulated road network and hospitals.

Run with the anaconda interpreter (plain `python3` has no SQLAlchemy):

    /opt/anaconda3/bin/python3.13 seed_data.py

This script is DESTRUCTIVE and idempotent: it truncates every table and rebuilds
from scratch, so running it twice gives exactly the same result.

Design notes
------------
* Road nodes form a 4x4 grid, roughly 2 km apart. A grid is not realistic street
  layout, but it is big enough that routing is non-trivial and every hospital
  snaps to its own distinct node.
* Edge weights are REAL haversine distances in km, not arbitrary numbers. This
  matters: it puts edge weights and the A* heuristic in the same unit, which is
  what makes A* behave as a real informed search rather than as Dijkstra.
* Two grid edges are deliberately missing to simulate a river with no bridge,
  so the shortest path is not simply the most direct-looking one.

All coordinates are SIMULATED. This is a portfolio project, not a medically
validated system.
"""

from sqlalchemy import text
from app.db import SessionLocal, engine, Base
# Importing the models registers every table on Base.metadata, which is what
# create_tables() below uses. EmergencyRequest is imported for that side effect
# even though this script never inserts one.
from app.models.models import (RoadNode, RoadEdge, Hospital, Ambulance,
                               EmergencyRequest)
from app.dsa.geo import haversine_km

# --- 1. Road network layout -------------------------------------------------

LATS = [28.44, 28.46, 28.48, 28.50]   # grid rows    (south -> north)
LNGS = [77.00, 77.02, 77.04, 77.06]   # grid columns (west  -> east)
GRID = 4

def node_id(row, col):
    """Row-major numbering, 1-indexed: row 0 is nodes 1-4, row 1 is 5-8, etc."""
    return row * GRID + col + 1

# Roads that do not exist - a river runs east-west between rows 1 and 2,
# and these two crossings have no bridge.
BLOCKED = {(5, 9), (6, 10)}

# --- 2. Hospitals -----------------------------------------------------------
# Each is placed slightly OFF its nearest node, so snapping does real work.
# Metro Care is intentionally left with 0 available beds: it is the live test
# case proving the heap's bed filter excludes full hospitals. Do not "fix" it.
# Facilities are assigned so the constraint is demonstrable, not decorative.
# Sunrise Medical is the hospital that normally wins on distance, and it has NO
# specialist units: a cardiac case therefore has to be sent past it to City
# Hospital, which is the whole point of modelling facilities at all.
HOSPITALS = [
    # name,              lat,      lng,     total, avail,  icu,   trauma, cardiac
    ("City Hospital",    28.4605, 77.0210,   50,    12,    True,  True,   True),
    ("Metro Care",       28.4795, 77.0405,   30,     0,    True,  False,  False),
    ("Sunrise Medical",  28.4410, 77.0395,   40,     8,    False, False,  False),
    ("Green Valley",     28.4990, 77.0205,   60,    25,    True,  False,  True),
    ("St. Mary",         28.4595, 77.0610,   35,     3,    False, True,   False),
]

AMBULANCES = [
    (28.4520, 77.0180, "available"),
    (28.4830, 77.0450, "available"),
    (28.4700, 77.0300, "busy"),
]


def create_tables():
    """Create any missing tables from the SQLAlchemy models.

    Until v1.2 the schema existed ONLY in the developer's local database --
    it had been typed into psql by hand and was never expressed in code. A
    fresh clone could not run: seed_data.py inserted into tables that nothing
    created, failing with 'relation "road_edges" does not exist'.

    models.py already describes every table, so create_all() is the whole fix.
    It is safe to run repeatedly: existing tables are left untouched.

    NOTE: create_all does NOT alter existing tables. If you add a column to a
    model, an already-created table will not gain it -- that needs a migration
    tool (Alembic), which this project does not use.
    """
    Base.metadata.create_all(engine)
    print(f"Schema ready: {', '.join(sorted(Base.metadata.tables))}")


def seed():
    create_tables()
    db = SessionLocal()
    try:
        # Wipe everything and reset id counters so ids are predictable (1, 2, 3...).
        db.execute(text(
            "TRUNCATE road_edges, road_nodes, hospitals, ambulances, "
            "emergency_requests RESTART IDENTITY CASCADE"
        ))
        db.commit()

        # --- nodes ---
        coords = {}
        for row in range(GRID):
            for col in range(GRID):
                nid = node_id(row, col)
                lat, lng = LATS[row], LNGS[col]
                coords[nid] = (lat, lng)
                db.add(RoadNode(id=nid, lat=lat, lng=lng))
        db.flush()

        # --- edges: connect each node to its right and lower neighbour ---
        edge_count = 0
        for row in range(GRID):
            for col in range(GRID):
                a = node_id(row, col)
                neighbours = []
                if col + 1 < GRID:
                    neighbours.append(node_id(row, col + 1))   # east
                if row + 1 < GRID:
                    neighbours.append(node_id(row + 1, col))   # north
                for b in neighbours:
                    if (a, b) in BLOCKED or (b, a) in BLOCKED:
                        continue
                    weight = round(haversine_km(*coords[a], *coords[b]), 3)
                    db.add(RoadEdge(from_node_id=a, to_node_id=b, weight=weight))
                    edge_count += 1

        # --- hospitals and ambulances ---
        for name, lat, lng, total, available, icu, trauma, cardiac in HOSPITALS:
            db.add(Hospital(name=name, latitude=lat, longitude=lng,
                            total_beds=total, available_beds=available,
                            has_icu=icu, has_trauma_unit=trauma,
                            has_cardiac_unit=cardiac))
        for lat, lng, status in AMBULANCES:
            db.add(Ambulance(current_lat=lat, current_lng=lng, status=status))

        db.commit()

        # Keep the id sequence in step with the explicit node ids we inserted,
        # so any future insert without an explicit id does not collide.
        db.execute(text(
            "SELECT setval('road_nodes_id_seq', (SELECT MAX(id) FROM road_nodes))"
        ))
        db.commit()

        # --- report ---
        print(f"Seeded {len(coords)} road nodes, {edge_count} road edges "
              f"({len(BLOCKED)} crossings deliberately missing),")
        print(f"       {len(HOSPITALS)} hospitals, {len(AMBULANCES)} ambulances.")
        print()
        print("Hospital -> nearest road node (this is what snapping will pick):")
        for name, lat, lng, _, available, icu, trauma, cardiac in HOSPITALS:
            best = min(coords, key=lambda n: haversine_km(lat, lng, *coords[n]))
            d = haversine_km(lat, lng, *coords[best])
            units = ", ".join(
                u for u, has in (("icu", icu), ("trauma", trauma),
                                 ("cardiac", cardiac)) if has
            ) or "none"
            print(f"  {name:<16} -> node {best:<3} ({d:.3f} km)  "
                  f"beds={available:<3} units: {units}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
