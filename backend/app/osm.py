"""Turning OpenStreetMap data into a routable graph.

Everything here is a PURE function over plain dictionaries: no network, no
database, no SQLAlchemy. Fetching is the seed script's job. That split is what
makes this testable with a hand-built five node graph instead of a 500 KB
download.

Why the raw data cannot be used directly
----------------------------------------
A real extract of this area is 5,904 ways and 22,240 nodes. Most of those nodes
are not junctions at all, they are shape points that trace the curve of a road.
Routing does not care where a road bends, only where it MEETS another road, so
the vast majority can be collapsed away without losing any accuracy: the road's
true curved length is kept as the edge weight.

Two reductions run here, in order:

1. Filter to arterial roads. Dropping residential side streets takes the extract
   from 5,904 ways to 536. This is a modelling choice as much as a performance
   one: an ambulance crossing a city uses main roads.
2. Collapse degree-2 chains. Any node with exactly two neighbours is a bend, not
   a junction, so the chain through it becomes a single edge whose weight is the
   summed length of every segment it replaced. 4,195 nodes become 463.

The result is 433 nodes and 643 edges after keeping the largest connected
component, which Dijkstra searches in well under a millisecond.
"""

from app.dsa.geo import haversine_km

# Road classes an ambulance would actually use. Residential streets are
# deliberately excluded: including them quadruples the graph for routes no
# emergency vehicle would take across a city.
ARTERIAL_ROADS = {
    "motorway", "trunk", "primary", "secondary", "tertiary",
    "motorway_link", "trunk_link", "primary_link", "secondary_link",
    "tertiary_link",
}

# Baseline congestion by road class, where 1.0 is free flowing. Bigger roads
# flow better. These figures are INVENTED, like every other traffic value in
# this project; OSM does not carry live traffic.
ROAD_CONGESTION = {
    "motorway": 1.05, "motorway_link": 1.15,
    "trunk": 1.15, "trunk_link": 1.25,
    "primary": 1.30, "primary_link": 1.35,
    "secondary": 1.50, "secondary_link": 1.55,
    "tertiary": 1.70, "tertiary_link": 1.70,
}
DEFAULT_CONGESTION = 1.5


def congestion_for(highway_type):
    """Baseline traffic factor for a road class."""
    return ROAD_CONGESTION.get(highway_type, DEFAULT_CONGESTION)


def build_adjacency(elements, allowed=ARTERIAL_ROADS):
    """Read an Overpass response into (adjacency, coords, road class per pair).

    `elements` is the raw list Overpass returns: node elements carry lat/lon,
    way elements carry an ordered list of node ids.
    """
    coords = {e["id"]: (e["lat"], e["lon"])
              for e in elements if e.get("type") == "node"}

    adjacency = {}
    road_class = {}

    for el in elements:
        if el.get("type") != "way":
            continue
        highway = el.get("tags", {}).get("highway")
        if allowed is not None and highway not in allowed:
            continue

        node_ids = [n for n in el.get("nodes", []) if n in coords]
        for a, b in zip(node_ids, node_ids[1:]):
            if a == b:
                continue
            adjacency.setdefault(a, set()).add(b)
            adjacency.setdefault(b, set()).add(a)
            road_class[(min(a, b), max(a, b))] = highway

    return adjacency, coords, road_class


def simplify(adjacency, coords, road_class=None):
    """Collapse chains of degree-2 nodes into single edges.

    Junctions (three or more neighbours) and dead ends (exactly one) are kept.
    Everything between them is walked, its segment lengths summed, and replaced
    by one edge carrying that true road length. The geometry is discarded but
    the DISTANCE is exact, which is all the router needs.

    Returns (kept_nodes, edges) where each edge is (a, b, km, highway_type).
    """
    kept = {n for n, nbrs in adjacency.items() if len(nbrs) != 2}

    # A ring road with no junction at all has no degree-2 exit point, so it
    # would vanish entirely. Keeping one arbitrary node breaks the tie.
    if not kept and adjacency:
        kept = {min(adjacency)}

    edges = []
    seen = set()

    for junction in kept:
        for first_step in adjacency[junction]:
            previous, current = junction, first_step
            distance = haversine_km(*coords[junction], *coords[first_step])
            klass = (road_class or {}).get(
                (min(junction, first_step), max(junction, first_step)))

            # Walk the chain until the next junction or dead end.
            guard = 0
            while current not in kept and guard < 100000:
                guard += 1
                nxt = next((n for n in adjacency[current] if n != previous), None)
                if nxt is None:
                    break
                distance += haversine_km(*coords[current], *coords[nxt])
                previous, current = current, nxt

            if current not in kept or current == junction:
                continue  # dangling chain, or a loop back to where we started

            key = (min(junction, current), max(junction, current))
            if key in seen:
                continue
            seen.add(key)
            edges.append((junction, current, distance, klass))

    return kept, edges


def largest_component(nodes, edges):
    """Keep only the biggest connected piece of the network.

    Filtering by road class leaves small islands: a slip road whose only
    connections were residential streets, for example. Routing to a node in a
    different component is impossible, so those are dropped rather than left to
    produce mysterious "no route found" answers later.

    Breadth first search over the edge list. Returns (nodes, edges).
    """
    if not edges:
        return set(), []

    neighbours = {}
    for a, b, *_ in edges:
        neighbours.setdefault(a, []).append(b)
        neighbours.setdefault(b, []).append(a)

    unvisited = set(neighbours)
    components = []
    while unvisited:
        start = unvisited.pop()
        component = {start}
        queue = [start]
        while queue:
            node = queue.pop()
            for nb in neighbours[node]:
                if nb not in component:
                    component.add(nb)
                    unvisited.discard(nb)
                    queue.append(nb)
        components.append(component)

    biggest = max(components, key=len)
    kept_edges = [e for e in edges if e[0] in biggest and e[1] in biggest]
    return biggest, kept_edges


def renumber(nodes, edges):
    """Map OSM ids onto 1..N.

    Necessary, not cosmetic: OSM node ids are now above 2^31, which overflows a
    Postgres INTEGER column. Small sequential ids are also far friendlier in a
    URL like /route?source=1&dest=42.

    Returns (osm_id -> new_id, renumbered_edges).
    """
    mapping = {osm_id: i for i, osm_id in enumerate(sorted(nodes), start=1)}
    renumbered = [(mapping[a], mapping[b], km, klass)
                  for a, b, km, klass in edges
                  if a in mapping and b in mapping]
    return mapping, renumbered
