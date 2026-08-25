"""Build the road network and hospitals from real OpenStreetMap data.

Run through seed_data.py, not directly.

What is real and what is not
----------------------------
REAL, from OpenStreetMap:
  * the road network: every junction, every road length, every road class
  * hospital names and their actual coordinates

INVENTED, because OSM does not carry it:
  * bed counts and which specialist units each hospital has
  * traffic congestion figures (derived from road class, not measured)
  * ambulance positions

So routes now follow real streets and hospital distances are real, but nothing
about capacity or traffic is a measurement. That distinction belongs in any
description of this project.

Offline by default
------------------
The Overpass responses are cached in backend/data/. The download is only
attempted when a cache file is missing, so seeding works on a plane and gives
byte-identical results every time. Delete the files in data/ to refresh.
"""

import hashlib
import json
import os
import urllib.parse
import urllib.request

from app.dsa.geo import haversine_km
from app.osm import (ARTERIAL_ROADS, build_adjacency, congestion_for,
                     largest_component, renumber, simplify)

# The area the project covers: part of Gurugram, India.
BBOX = (28.44, 77.00, 28.50, 77.06)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ROADS_CACHE = os.path.join(DATA_DIR, "osm_roads.json")
HOSPITALS_CACHE = os.path.join(DATA_DIR, "osm_hospitals.json")

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# How many of the real hospitals to keep. All 61 in this box would make an
# unreadable dashboard, and most are small clinics metres apart.
HOSPITAL_COUNT = 12
# Minimum separation, so the selection is spread across the map rather than
# clustered in one busy street.
HOSPITAL_MIN_SPACING_KM = 0.8

AMBULANCE_COUNT = 3


def _overpass(query):
    request = urllib.request.Request(
        OVERPASS_URL,
        data=urllib.parse.urlencode({"data": query}).encode(),
        headers={"User-Agent": "ambulance-router-portfolio/1.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def _cached(path, query, label):
    """Return parsed JSON, downloading and caching only if the file is absent."""
    if os.path.exists(path):
        with open(path) as handle:
            return json.load(handle)

    print(f"  downloading {label} from OpenStreetMap (first run only)...")
    os.makedirs(DATA_DIR, exist_ok=True)
    raw = _overpass(query)
    with open(path, "wb") as handle:
        handle.write(raw)
    print(f"  cached {len(raw) / 1024:.0f} KB to {os.path.relpath(path)}")
    return json.loads(raw)


def fetch_roads():
    types = "|".join(sorted(ARTERIAL_ROADS))
    bbox = ",".join(str(v) for v in BBOX)
    query = (f'[out:json][timeout:90];'
             f'way["highway"~"^({types})$"]({bbox});'
             f'out body;>;out skel qt;')
    return _cached(ROADS_CACHE, query, "road network")["elements"]


def fetch_hospitals():
    bbox = ",".join(str(v) for v in BBOX)
    query = (f'[out:json][timeout:60];'
             f'(node["amenity"="hospital"]({bbox});'
             f'way["amenity"="hospital"]({bbox}););out center;')
    return _cached(HOSPITALS_CACHE, query, "hospitals")["elements"]


def build_network():
    """Real OSM roads reduced to a routable graph.

    Returns (coords_by_new_id, edges) where each edge is
    (from_id, to_id, km, traffic_factor).
    """
    elements = fetch_roads()

    adjacency, coords, road_class = build_adjacency(elements, ARTERIAL_ROADS)
    kept, edges = simplify(adjacency, coords, road_class)
    kept, edges = largest_component(kept, edges)
    mapping, renumbered = renumber(kept, edges)

    new_coords = {new: coords[osm] for osm, new in mapping.items()}
    final_edges = [(a, b, round(km, 4), congestion_for(klass))
                   for a, b, km, klass in renumbered]

    return new_coords, final_edges


def _deterministic_int(text, low, high):
    """A stable pseudo random number derived from a name.

    Python's hash() is salted per process, so it would give different bed counts
    on every run. Hashing explicitly keeps seeding reproducible.
    """
    digest = hashlib.md5(text.encode()).digest()
    return low + (int.from_bytes(digest[:4], "big") % (high - low + 1))


def select_hospitals(elements, node_coords):
    """Pick a spread of real hospitals and give them invented capacity.

    Greedy spacing: walk the list and keep a hospital only if it is at least
    HOSPITAL_MIN_SPACING_KM from every one already chosen. Without this the
    selection clusters, because real clinics sit side by side on main roads.
    """
    candidates = []
    for el in elements:
        name = el.get("tags", {}).get("name")
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if name and lat and lon:
            candidates.append((name.strip(), float(lat), float(lon)))

    candidates.sort(key=lambda h: h[0])  # stable order, independent of Overpass

    chosen = []
    for name, lat, lon in candidates:
        if len(chosen) >= HOSPITAL_COUNT:
            break
        if all(haversine_km(lat, lon, c[1], c[2]) >= HOSPITAL_MIN_SPACING_KM
               for c in chosen):
            chosen.append((name, lat, lon))

    hospitals = []
    for index, (name, lat, lon) in enumerate(chosen):
        total = _deterministic_int(name, 3, 12) * 5          # 15 to 60 beds
        available = _deterministic_int(name + "beds", 0, total)

        # Facilities spread deterministically so the mix is varied but stable.
        marker = _deterministic_int(name + "units", 0, 7)
        has_icu = bool(marker & 1)
        has_trauma = bool(marker & 2)
        has_cardiac = bool(marker & 4)

        # Guarantee the two cases the demos rely on: one hospital with no free
        # beds, and one with no specialist units at all.
        if index == 1:
            available = 0
        if index == 2:
            has_icu = has_trauma = has_cardiac = False
        # ...and guarantee somewhere a cardiac case can actually go.
        if index == 0:
            has_icu = has_trauma = has_cardiac = True
            available = max(available, 5)

        hospitals.append({
            "name": name, "latitude": lat, "longitude": lon,
            "total_beds": total, "available_beds": min(available, total),
            "has_icu": has_icu, "has_trauma_unit": has_trauma,
            "has_cardiac_unit": has_cardiac,
        })

    return hospitals


def select_ambulances(node_coords):
    """Park ambulances on real junctions, spread across the network."""
    ids = sorted(node_coords)
    if not ids:
        return []
    step = max(1, len(ids) // (AMBULANCE_COUNT + 1))
    picks = [ids[step * (i + 1)] for i in range(AMBULANCE_COUNT)]
    return [
        {"current_lat": node_coords[n][0], "current_lng": node_coords[n][1],
         "status": "available" if i < AMBULANCE_COUNT - 1 else "busy"}
        for i, n in enumerate(picks)
    ]
