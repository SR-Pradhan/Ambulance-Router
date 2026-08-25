"""Shared road-network loading.

Every endpoint that routes needs the same two things: a Graph built from
road_edges, and a {node_id: (lat, lng)} map from road_nodes. This was copy-
pasted in each endpoint; keeping it here means there is one definition of "the
road network" and one place to add caching later.

Note this module DOES touch the database, so it deliberately lives outside
dsa/ -- the dsa/ package stays pure and importable without SQLAlchemy.
"""

from datetime import datetime

from app.models.models import RoadNode, RoadEdge
from app.dsa.graph import Graph
from app.dsa.geo import haversine_km
from app.dsa.traffic import travel_time_minutes


def load_road_network(db, hour=None):
    """Return (graph, coords) for the whole road network.

    **Edge weights are TRAVEL TIME IN MINUTES, not kilometres.** That is the
    point of the traffic model: the router is asked for the FASTEST route, and
    a congested short road can lose to a clear longer one. Every consumer of
    this graph is therefore working in minutes.

    `hour` selects the time of day congestion. It defaults to now, so routes
    change across the day; pass an explicit hour to make results reproducible.

    Rebuilt from the database on every call. Fine at 16 nodes; the obvious
    optimisation is to build once at startup and invalidate when roads change.
    """
    if hour is None:
        hour = datetime.now().hour

    coords = {n.id: (n.lat, n.lng) for n in db.query(RoadNode).all()}

    graph = Graph()
    for e in db.query(RoadEdge).all():
        minutes = travel_time_minutes(e.weight, e.traffic_factor, hour)
        graph.add_edge(e.from_node_id, e.to_node_id, minutes)

    return graph, coords


def path_length_km(path, coords):
    """Physical length of a path in km.

    Needed because the graph is now weighted in minutes: summing edge weights
    gives a duration, not a distance. Anything that wants real kilometres (the
    API response, live position interpolation) has to measure the coordinates.
    """
    if not path or len(path) < 2:
        return 0.0
    total = 0.0
    for a, b in zip(path, path[1:]):
        if a in coords and b in coords:
            total += haversine_km(*coords[a], *coords[b])
    return total


def path_to_coords(path, coords):
    """Turn a list of node ids into a list of (lat, lng) waypoints."""
    if not path:
        return []
    return [coords[n] for n in path if n in coords]
