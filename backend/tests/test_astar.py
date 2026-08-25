import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))

from dsa.graph import Graph
from dsa.dijkstra import dijkstra
from dsa.astar import astar, heuristic
from dsa.geo import haversine_km


# Real coordinates, and edge weights DERIVED from those coordinates.
#
# This matters. The earlier version of this file used arbitrary weights
# (4, 2, 1, 5, 8) with unrelated coordinates like (0,0) and (3,2). Once the
# heuristic returns real kilometres, those two are in different units: read as
# lat/lng, (0,0) -> (3,2) is ~400 km against an edge path costing 8, a ~50x
# overestimate. An overestimating heuristic is INADMISSIBLE and A* stops
# guaranteeing the shortest path.
#
# Keeping weights and heuristic in the same unit is not a detail -- it is the
# precondition that makes A* correct.
COORDS = {
    "A": (28.44, 77.00),
    "B": (28.46, 77.02),
    "C": (28.44, 77.02),
    "D": (28.48, 77.04),
    "E": (28.46, 77.00),
}

EDGES = [("A", "C"), ("A", "E"), ("C", "B"), ("E", "B"), ("B", "D"), ("C", "D")]


def make_graph_and_coords():
    g = Graph()
    for u, v in EDGES:
        g.add_edge(u, v, haversine_km(*COORDS[u], *COORDS[v]))
    return g, COORDS


def test_astar_matches_dijkstra_distance():
    g, coords = make_graph_and_coords()

    d_path, d_dist = dijkstra(g, "A", "D")
    a_path, a_dist = astar(g, "A", "D", coords)

    print(f"Test 1 - Dijkstra: {d_path} {d_dist:.3f} km")
    print(f"         A*:       {a_path} {a_dist:.3f} km")

    assert abs(d_dist - a_dist) < 1e-9, f"Distance mismatch: {d_dist} vs {a_dist}"


def test_astar_no_path():
    g, coords = make_graph_and_coords()
    g.add_node("Z")
    coords = dict(coords)
    coords["Z"] = (28.90, 77.90)

    path, dist = astar(g, "A", "Z", coords)
    print("Test 2 - No path:", path, dist)
    assert dist == float('inf')


def test_astar_same_source_dest():
    g, coords = make_graph_and_coords()

    path, dist = astar(g, "A", "A", coords)
    print("Test 3 - Same node:", path, dist)
    assert dist == 0
    assert path == ["A"]


def test_heuristic_is_admissible():
    """A* is only optimal if the heuristic NEVER overestimates.

    For every node, the straight-line estimate to the goal must be <= the true
    shortest road distance to the goal. This is the property the old test data
    silently violated.
    """
    g, coords = make_graph_and_coords()
    print("Test 4 - Admissibility (h must never exceed true cost):")

    for node in g.adj:
        _, true_cost = dijkstra(g, node, "D")
        h = heuristic(coords, node, "D")
        print(f"           {node}: h={h:.3f} km  true={true_cost:.3f} km")
        assert h <= true_cost + 1e-9, (
            f"INADMISSIBLE at {node}: heuristic {h} > true cost {true_cost}"
        )


def test_heuristic_is_in_same_unit_as_weights():
    """The units bug, caught directly.

    A heuristic that is orders of magnitude smaller than a single edge weight
    contributes nothing, and A* silently degenerates into Dijkstra. Here they
    must be comparable.
    """
    g, coords = make_graph_and_coords()
    weights = [w for node in g.adj for _, w in g.get_neighbors(node)]
    avg_weight = sum(weights) / len(weights)
    h = heuristic(coords, "A", "D")

    ratio = h / avg_weight
    print(f"Test 5 - Units: h(A->D)={h:.3f} km, avg edge={avg_weight:.3f} km, "
          f"ratio={ratio:.2f}")
    assert 0.1 < ratio < 10, (
        f"Heuristic and edge weights look like different units (ratio {ratio})"
    )


def test_astar_expands_no_more_nodes_than_dijkstra():
    """A* should never explore MORE than Dijkstra, given an admissible heuristic."""
    g, coords = make_graph_and_coords()

    d_stats, a_stats = {}, {}
    dijkstra(g, "A", "D", stats=d_stats)
    astar(g, "A", "D", coords, stats=a_stats)

    print(f"Test 6 - Nodes expanded: Dijkstra {d_stats['nodes_expanded']}, "
          f"A* {a_stats['nodes_expanded']}")
    assert a_stats["nodes_expanded"] <= d_stats["nodes_expanded"]


if __name__ == "__main__":
    test_astar_matches_dijkstra_distance()
    test_astar_no_path()
    test_astar_same_source_dest()
    test_heuristic_is_admissible()
    test_heuristic_is_in_same_unit_as_weights()
    test_astar_expands_no_more_nodes_than_dijkstra()
    print("\nAll A* tests passed.")
