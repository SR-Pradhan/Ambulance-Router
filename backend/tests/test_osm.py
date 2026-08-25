import sys
import os

# This test puts BACKEND on the path, not backend/app like the dsa tests do.
# app/osm.py imports app.dsa.geo, so the `app` package itself has to be
# importable; adding app/ directly would make osm a top level module and that
# import would fail.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.osm import (build_adjacency, simplify, largest_component, renumber,
                     congestion_for, ARTERIAL_ROADS)
from app.dsa.geo import haversine_km


def overpass(nodes, ways):
    """Build a fake Overpass response, so these tests need no network."""
    els = [{"type": "node", "id": nid, "lat": lat, "lon": lon}
           for nid, (lat, lon) in nodes.items()]
    els += [{"type": "way", "id": 1000 + i, "nodes": ns, "tags": {"highway": hw}}
            for i, (ns, hw) in enumerate(ways)]
    return els


# A straight road A-B-C-D where B and C are bends, plus a spur off C.
STRAIGHT = {
    1: (28.44, 77.00), 2: (28.44, 77.01), 3: (28.44, 77.02), 4: (28.44, 77.03),
}


def test_build_adjacency_links_consecutive_nodes():
    adj, coords, klass = build_adjacency(
        overpass(STRAIGHT, [([1, 2, 3, 4], "primary")]))
    print("Test 1 - Adjacency:", {k: sorted(v) for k, v in sorted(adj.items())})
    assert sorted(adj[2]) == [1, 3]
    assert len(coords) == 4
    assert klass[(1, 2)] == "primary"


def test_residential_roads_are_filtered_out():
    els = overpass(STRAIGHT, [([1, 2], "primary"), ([3, 4], "residential")])
    adj, _, _ = build_adjacency(els, allowed=ARTERIAL_ROADS)
    print("Test 2 - Residential excluded, nodes kept:", sorted(adj))
    assert sorted(adj) == [1, 2]


def test_simplify_collapses_a_chain_but_keeps_its_length():
    """The core claim: geometry is discarded, distance is not."""
    adj, coords, klass = build_adjacency(
        overpass(STRAIGHT, [([1, 2, 3, 4], "primary")]))
    kept, edges = simplify(adj, coords, klass)

    print(f"Test 3 - 4 nodes -> {len(kept)} kept, {len(edges)} edge(s)")
    assert kept == {1, 4}, "only the two endpoints are junctions"
    assert len(edges) == 1

    a, b, km, hw = edges[0]
    true_length = (haversine_km(*STRAIGHT[1], *STRAIGHT[2])
                   + haversine_km(*STRAIGHT[2], *STRAIGHT[3])
                   + haversine_km(*STRAIGHT[3], *STRAIGHT[4]))
    print(f"         collapsed edge {a}->{b}: {km:.4f} km, "
          f"true summed length {true_length:.4f} km")
    assert abs(km - true_length) < 1e-9, "collapsing must preserve the distance"


def test_junctions_are_kept():
    nodes = dict(STRAIGHT); nodes[5] = (28.45, 77.02)
    adj, coords, klass = build_adjacency(
        overpass(nodes, [([1, 2, 3, 4], "primary"), ([3, 5], "secondary")]))
    kept, edges = simplify(adj, coords, klass)
    print(f"Test 4 - With a spur at node 3: kept {sorted(kept)}")
    assert 3 in kept, "node 3 now has three neighbours, so it is a junction"
    assert len(edges) == 3


def test_largest_component_drops_islands():
    nodes = dict(STRAIGHT); nodes[9] = (28.49, 77.05); nodes[10] = (28.49, 77.055)
    adj, coords, klass = build_adjacency(
        overpass(nodes, [([1, 2, 3, 4], "primary"), ([9, 10], "primary")]))
    kept, edges = simplify(adj, coords, klass)
    big, big_edges = largest_component(kept, edges)
    print(f"Test 5 - {len(kept)} nodes in {len(edges)} edges -> "
          f"largest component {sorted(big)}")
    assert big == {1, 4}
    assert len(big_edges) == 1


def test_renumber_maps_huge_osm_ids_into_range():
    """OSM ids exceed 2^31 and would overflow a Postgres INTEGER column."""
    huge = {11_000_000_001, 11_000_000_002, 11_000_000_003}
    edges = [(11_000_000_001, 11_000_000_002, 1.0, "primary"),
             (11_000_000_002, 11_000_000_003, 2.0, "primary")]
    mapping, renumbered = renumber(huge, edges)
    print("Test 6 - Renumbered:", mapping, "->", renumbered)
    assert sorted(mapping.values()) == [1, 2, 3]
    assert all(a < 2**31 and b < 2**31 for a, b, _, _ in renumbered)
    assert renumbered[0][2] == 1.0, "weights must survive renumbering"


def test_congestion_scales_with_road_class():
    print("Test 7 - Congestion:", {k: congestion_for(k) for k in
                                   ("motorway", "primary", "tertiary", "unknown")})
    assert congestion_for("motorway") < congestion_for("primary") \
        < congestion_for("tertiary")
    assert congestion_for("something_new") > 1.0


def test_empty_input_is_safe():
    adj, coords, klass = build_adjacency([])
    kept, edges = simplify(adj, coords, klass)
    big, big_edges = largest_component(kept, edges)
    print("Test 8 - Empty input:", adj, kept, edges, big, big_edges)
    assert (adj, kept, edges, big, big_edges) == ({}, set(), [], set(), [])


if __name__ == "__main__":
    test_build_adjacency_links_consecutive_nodes()
    test_residential_roads_are_filtered_out()
    test_simplify_collapses_a_chain_but_keeps_its_length()
    test_junctions_are_kept()
    test_largest_component_drops_islands()
    test_renumber_maps_huge_osm_ids_into_range()
    test_congestion_scales_with_road_class()
    test_empty_input_is_safe()
    print("\nAll OSM tests passed.")
