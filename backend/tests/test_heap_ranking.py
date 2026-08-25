import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))

from dsa.heap_ranking import rank_hospitals


def test_basic_ranking():
    hospitals = [
        {"name": "H1", "distance": 5.0, "available_beds": 2},
        {"name": "H2", "distance": 2.0, "available_beds": 1},
        {"name": "H3", "distance": 8.0, "available_beds": 4},
    ]
    result = rank_hospitals(hospitals, top_k=2)
    print("Test 1 - Basic ranking:", [h["name"] for h in result])
    assert [h["name"] for h in result] == ["H2", "H1"], f"Unexpected order: {result}"


def test_excludes_zero_beds():
    hospitals = [
        {"name": "H1", "distance": 1.0, "available_beds": 0},
        {"name": "H2", "distance": 3.0, "available_beds": 5},
    ]
    result = rank_hospitals(hospitals, top_k=2)
    print("Test 2 - Excludes zero beds:", [h["name"] for h in result])
    assert len(result) == 1
    assert result[0]["name"] == "H2"


def test_top_k_larger_than_list():
    hospitals = [
        {"name": "H1", "distance": 4.0, "available_beds": 3},
    ]
    result = rank_hospitals(hospitals, top_k=5)
    print("Test 3 - top_k larger than list:", [h["name"] for h in result])
    assert len(result) == 1
    assert result[0]["name"] == "H1"


def test_empty_list():
    result = rank_hospitals([], top_k=3)
    print("Test 4 - Empty list:", result)
    assert result == []


def test_all_zero_beds():
    hospitals = [
        {"name": "H1", "distance": 1.0, "available_beds": 0},
        {"name": "H2", "distance": 2.0, "available_beds": 0},
    ]
    result = rank_hospitals(hospitals, top_k=2)
    print("Test 5 - All zero beds:", result)
    assert result == []


if __name__ == "__main__":
    test_basic_ranking()
    test_excludes_zero_beds()
    test_top_k_larger_than_list()
    test_empty_list()
    test_all_zero_beds()
    print("\nAll heap ranking tests passed.")