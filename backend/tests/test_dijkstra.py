import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))

from dsa.graph import Graph
from dsa.dijkstra import dijkstra, dijkstra_all, reconstruct_path


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


def _sample_graph():
    g = Graph()
    g.add_edge("A", "B", 4)
    g.add_edge("A", "C", 2)
    g.add_edge("C", "B", 1)
    g.add_edge("B", "D", 5)
    g.add_edge("C", "D", 8)
    return g


def test_dijkstra_all_matches_single_target():
    """One dijkstra_all run must agree with dijkstra() called per destination.

    Same cross-check idea as the A* tests: two independent implementations
    agreeing is strong evidence both are correct.
    """
    g = _sample_graph()
    distances, prev = dijkstra_all(g, "A")

    print("Test 5 - dijkstra_all vs dijkstra, per node:")
    for node in g.adj:
        _, expected = dijkstra(g, "A", node)
        print(f"          {node}: all={distances[node]}  single={expected}")
        assert distances[node] == expected, (
            f"Mismatch at {node}: dijkstra_all={distances[node]}, dijkstra={expected}"
        )


def test_dijkstra_all_marks_unreachable():
    g = Graph()
    g.add_edge("A", "B", 4)
    g.add_node("Z")  # isolated

    distances, prev = dijkstra_all(g, "A")
    print("Test 6 - Unreachable node distance:", distances["Z"])
    assert distances["Z"] == float("inf")
    assert distances["A"] == 0


def test_reconstruct_path_matches_dijkstra():
    g = _sample_graph()
    distances, prev = dijkstra_all(g, "A")

    path = reconstruct_path(prev, "A", "D")
    expected, _ = dijkstra(g, "A", "D")
    print("Test 7 - Reconstructed path:", path, "vs dijkstra:", expected)
    assert path == expected == ["A", "C", "B", "D"]


def test_reconstruct_path_unreachable_returns_none():
    g = Graph()
    g.add_edge("A", "B", 4)
    g.add_node("Z")

    distances, prev = dijkstra_all(g, "A")
    path = reconstruct_path(prev, "A", "Z")
    print("Test 8 - Path to unreachable node:", path)
    assert path is None, "Unreachable target must give None, not a bogus one-node path"


def test_reconstruct_path_source_to_itself():
    """The case that makes `source` a required argument.

    Both a source node and an unreachable node have prev = None, so without
    knowing the source these two are indistinguishable. Source->source is a
    real path of length 1; unreachable (test 8) must be None.
    """
    g = _sample_graph()
    distances, prev = dijkstra_all(g, "A")

    path = reconstruct_path(prev, "A", "A")
    print("Test 9 - Source to itself:", path)
    assert path == ["A"]


if __name__ == "__main__":
    test_basic_path()
    test_no_path_exists()
    test_single_node()
    test_multiple_equal_paths()
    test_dijkstra_all_matches_single_target()
    test_dijkstra_all_marks_unreachable()
    test_reconstruct_path_matches_dijkstra()
    test_reconstruct_path_unreachable_returns_none()
    test_reconstruct_path_source_to_itself()
    print("\nAll tests passed.")