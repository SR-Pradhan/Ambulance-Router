import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))

from dsa.geo import (haversine_km, snap_to_node,
                     interpolate_point, position_along_path)


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


# A straight 2-leg path: (28.44,77.00) -> (28.44,77.02) -> (28.44,77.04)
# Purely east-west at constant latitude, so each leg is the same length and the
# arithmetic is checkable by hand.
STRAIGHT_PATH = [(28.44, 77.00), (28.44, 77.02), (28.44, 77.04)]


def test_interpolate_midpoint():
    lat, lng = interpolate_point(28.44, 77.00, 28.44, 77.02, 0.5)
    print("Test 9 - Midpoint:", lat, round(lng, 5))
    assert lat == 28.44
    assert abs(lng - 77.01) < 1e-9


def test_interpolate_clamps():
    start = interpolate_point(0, 0, 10, 10, -5)
    end = interpolate_point(0, 0, 10, 10, 99)
    print("Test 10 - Clamping:", start, end)
    assert start == (0, 0)
    assert end == (10, 10)


def test_position_at_start_and_end():
    lat, lng, travelled, total, finished = position_along_path(STRAIGHT_PATH, 0)
    print(f"Test 11 - At start: ({lat}, {lng}) total={total:.3f} km")
    assert (lat, lng) == STRAIGHT_PATH[0]
    assert not finished

    lat, lng, travelled, total, finished = position_along_path(STRAIGHT_PATH, 999)
    print(f"Test 12 - Overshoot clamps to end: ({lat}, {lng}) finished={finished}")
    assert (lat, lng) == STRAIGHT_PATH[-1]
    assert finished


def test_position_halfway_lands_on_middle_waypoint():
    """Half the total distance must land exactly on the middle waypoint,
    because both legs are the same length."""
    _, _, _, total, _ = position_along_path(STRAIGHT_PATH, 0)
    lat, lng, travelled, _, finished = position_along_path(STRAIGHT_PATH, total / 2)
    print(f"Test 13 - Halfway: ({lat}, {round(lng, 6)}) after {travelled:.3f} km")
    assert abs(lng - 77.02) < 1e-6, f"Expected to land on 77.02, got {lng}"
    assert not finished


def test_position_quarter_way_is_inside_first_leg():
    _, _, _, total, _ = position_along_path(STRAIGHT_PATH, 0)
    lat, lng, _, _, _ = position_along_path(STRAIGHT_PATH, total / 4)
    print(f"Test 14 - Quarter way: ({lat}, {round(lng, 6)})")
    assert 77.00 < lng < 77.02, "Quarter of the way must be inside the first leg"
    assert abs(lng - 77.01) < 1e-6


def test_position_empty_and_single_point():
    print("Test 15 - Empty path:", position_along_path([], 5))
    assert position_along_path([], 5) is None

    result = position_along_path([(28.44, 77.00)], 5)
    print("Test 16 - Single point path:", result)
    assert result[:2] == (28.44, 77.00)
    assert result[4] is True


if __name__ == "__main__":
    test_same_point_is_zero()
    test_known_distance_bbsr_to_cuttack()
    test_known_distance_delhi_to_mumbai()
    test_symmetric()
    test_snap_picks_nearest()
    test_snap_exact_node_is_zero()
    test_snap_empty_returns_none()
    test_snap_is_not_fooled_by_longitude()
    test_interpolate_midpoint()
    test_interpolate_clamps()
    test_position_at_start_and_end()
    test_position_halfway_lands_on_middle_waypoint()
    test_position_quarter_way_is_inside_first_leg()
    test_position_empty_and_single_point()
    print("\nAll geo tests passed.")
