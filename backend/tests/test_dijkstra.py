import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))

from dsa.graph import Graph
from dsa.dijkstra import dijkstra


def test_basic_path():
    g = Graph()
    g.add_edge("A", "B", 4)
    g.add_edge("A", "C", 2)
    g.add_edge("C", "B", 1)
    g.add_edge("B", "D", 5)
    g.add_edge("C", "D", 8)

    path, dist = dijkstra(g, "A", "D")
    print("Test 1 - Basic path:", path, dist)
    assert dist == 8, f"Expected 8, got {dist}"
    assert path == ["A", "C", "B", "D"], f"Unexpected path: {path}"


def test_no_path_exists():
    g = Graph()
    g.add_edge("A", "B", 4)
    g.add_node("Z")  # isolated node, no edges

    path, dist = dijkstra(g, "A", "Z")
    print("Test 2 - No path:", path, dist)
    assert dist == float('inf'), "Expected inf distance for unreachable node"


def test_single_node():
    g = Graph()
    g.add_node("A")

    path, dist = dijkstra(g, "A", "A")
    print("Test 3 - Same source/dest:", path, dist)
    assert dist == 0
    assert path == ["A"]


def test_multiple_equal_paths():
    g = Graph()
    g.add_edge("A", "B", 3)
    g.add_edge("A", "C", 3)
    g.add_edge("B", "D", 3)
    g.add_edge("C", "D", 3)

    path, dist = dijkstra(g, "A", "D")
    print("Test 4 - Equal paths:", path, dist)
    assert dist == 6, f"Expected 6, got {dist}"
    # path could be A->B->D or A->C->D, both valid — just check distance


if __name__ == "__main__":
    test_basic_path()
    test_no_path_exists()
    test_single_node()
    test_multiple_equal_paths()
    print("\nAll tests passed.")