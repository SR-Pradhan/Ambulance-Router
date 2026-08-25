import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))

from dsa.geo import haversine_km, snap_to_node


def test_same_point_is_zero():
    d = haversine_km(20.2961, 85.8245, 20.2961, 85.8245)
    print("Test 1 - Same point:", d)
    assert d == 0.0


def test_known_distance_bbsr_to_cuttack():
    # Bhubaneswar -> Cuttack, real-world ~22 km apart
    d = haversine_km(20.2961, 85.8245, 20.4625, 85.8830)
    print("Test 2 - Bhubaneswar to Cuttack:", round(d, 2), "km")
    assert 18 < d < 26, f"Unexpected distance: {d}"


def test_known_distance_delhi_to_mumbai():
    # Delhi -> Mumbai, real-world ~1150 km apart
    d = haversine_km(28.6139, 77.2090, 19.0760, 72.8777)
    print("Test 3 - Delhi to Mumbai:", round(d, 2), "km")
    assert 1100 < d < 1200, f"Unexpected distance: {d}"


def test_symmetric():
    a = haversine_km(20.2961, 85.8245, 20.4625, 85.8830)
    b = haversine_km(20.4625, 85.8830, 20.2961, 85.8245)
    print("Test 4 - Symmetry:", round(a, 4), round(b, 4))
    assert abs(a - b) < 1e-9


NODES = {
    1: (28.44, 77.00),
    2: (28.44, 77.02),
    5: (28.46, 77.00),
    6: (28.46, 77.02),
}


def test_snap_picks_nearest():
    # Just north-east of node 1, but still much closer to it than to any other.
    node, d = snap_to_node(28.4405, 77.0005, NODES)
    print("Test 5 - Snap picks nearest:", node, round(d, 4), "km")
    assert node == 1, f"Expected node 1, got {node}"
    assert d < 0.1


def test_snap_exact_node_is_zero():
    node, d = snap_to_node(28.46, 77.02, NODES)
    print("Test 6 - Snap onto exact node:", node, d)
    assert node == 6
    assert d == 0.0


def test_snap_empty_returns_none():
    node, d = snap_to_node(28.44, 77.00, {})
    print("Test 7 - Snap with no nodes:", node, d)
    assert node is None
    assert d == float("inf")


def test_snap_is_not_fooled_by_longitude():
    """Degrees are not distances - this is the bug haversine exists to prevent.

    From the patient point, NORTH is 0.02 degrees away and EAST is 0.02 degrees
    away, so a naive comparison of raw degree differences would call them tied.
    In real km they are not: 0.02 deg of latitude is ~2.22 km, while 0.02 deg of
    longitude at this latitude is only ~1.96 km. EAST must win.
    """
    patient = (28.44, 77.00)
    nodes = {
        "NORTH": (28.46, 77.00),   # 0.02 deg latitude  -> ~2.22 km
        "EAST":  (28.44, 77.02),   # 0.02 deg longitude -> ~1.96 km
    }
    node, d = snap_to_node(*patient, nodes)

    d_north = haversine_km(*patient, *nodes["NORTH"])
    d_east = haversine_km(*patient, *nodes["EAST"])
    print(f"Test 8 - Degrees vs km: NORTH {d_north:.3f} km, "
          f"EAST {d_east:.3f} km -> picked {node}")

    assert node == "EAST", "Snapping must compare real km, not raw degree differences"
    assert d_east < d_north


if __name__ == "__main__":
    test_same_point_is_zero()
    test_known_distance_bbsr_to_cuttack()
    test_known_distance_delhi_to_mumbai()
    test_symmetric()
    test_snap_picks_nearest()
    test_snap_exact_node_is_zero()
    test_snap_empty_returns_none()
    test_snap_is_not_fooled_by_longitude()
    print("\nAll geo tests passed.")
