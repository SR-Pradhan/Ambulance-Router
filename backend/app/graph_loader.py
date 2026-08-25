"""Shared road-network loading.

Every endpoint that routes needs the same two things: a Graph built from
road_edges, and a {node_id: (lat, lng)} map from road_nodes. This was copy-
pasted in each endpoint; keeping it here means there is one definition of "the
road network" and one place to add caching later.

Note this module DOES touch the database, so it deliberately lives outside
dsa/ -- the dsa/ package stays pure and importable without SQLAlchemy.
"""

from app.models.models import RoadNode, RoadEdge
from app.dsa.graph import Graph


def load_road_network(db):
    """Return (graph, coords) for the whole road network.

    Rebuilt from the database on every call. Fine at 16 nodes; the obvious
    optimisation is to build once at startup and invalidate when roads change.
    """
    coords = {n.id: (n.lat, n.lng) for n in db.query(RoadNode).all()}

    graph = Graph()
    for e in db.query(RoadEdge).all():
        graph.add_edge(e.from_node_id, e.to_node_id, e.weight)

    return graph, coords


def path_to_coords(path, coords):
    """Turn a list of node ids into a list of (lat, lng) waypoints."""
    if not path:
        return []
    return [coords[n] for n in path if n in coords]
