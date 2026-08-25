import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))

from dsa.geo import haversine_km


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


if __name__ == "__main__":
    test_same_point_is_zero()
    test_known_distance_bbsr_to_cuttack()
    test_known_distance_delhi_to_mumbai()
    test_symmetric()
    print("\nAll geo tests passed.")
