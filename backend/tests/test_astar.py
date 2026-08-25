import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))

from dsa.graph import Graph
from dsa.dijkstra import dijkstra
from dsa.astar import astar


def make_graph_and_coords():
    g = Graph()
    g.add_edge("A", "B", 4)
    g.add_edge("A", "C", 2)
    g.add_edge("C", "B", 1)
    g.add_edge("B", "D", 5)
    g.add_edge("C", "D", 8)

    # arbitrary coordinates, just need to be consistent/plausible
    coords = {
        "A": (0, 0),
        "B": (2, 1),
        "C": (1, 0),
        "D": (3, 2),
    }
    return g, coords


def test_astar_matches_dijkstra_distance():
    g, coords = make_graph_and_coords()

    d_path, d_dist = dijkstra(g, "A", "D")
    a_path, a_dist = astar(g, "A", "D", coords)

    print("Dijkstra:", d_path, d_dist)
    print("A*:      ", a_path, a_dist)

    assert d_dist == a_dist, f"Distance mismatch: dijkstra={d_dist}, astar={a_dist}"


def test_astar_no_path():
    g, coords = make_graph_and_coords()
    g.add_node("Z")
    coords["Z"] = (10, 10)

    path, dist = astar(g, "A", "Z", coords)
    print("No path:", path, dist)
    assert dist == float('inf')


def test_astar_same_source_dest():
    g, coords = make_graph_and_coords()

    path, dist = astar(g, "A", "A", coords)
    print("Same node:", path, dist)
    assert dist == 0
    assert path == ["A"]


if __name__ == "__main__":
    test_astar_matches_dijkstra_distance()
    test_astar_no_path()
    test_astar_same_source_dest()
    print("\nAll A* tests passed.")