import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))

from dsa.heap_ranking import rank_hospitals, rank_by_distance


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


def test_rank_by_distance_picks_nearest():
    ambulances = [
        {"id": 1, "distance": 5.4},
        {"id": 2, "distance": 1.2},
        {"id": 3, "distance": 3.9},
    ]
    result = rank_by_distance(ambulances, top_k=1)
    print("Test 6 - Nearest ambulance:", result)
    assert len(result) == 1
    assert result[0]["id"] == 2


def test_rank_by_distance_empty():
    result = rank_by_distance([], top_k=1)
    print("Test 7 - No ambulances available:", result)
    assert result == []


def test_rank_by_distance_top_k_larger_than_list():
    items = [{"id": 1, "distance": 2.0}]
    result = rank_by_distance(items, top_k=5)
    print("Test 8 - top_k larger than list:", result)
    assert len(result) == 1


def test_rank_by_distance_orders_all():
    items = [{"id": 1, "distance": 9.0},
             {"id": 2, "distance": 1.0},
             {"id": 3, "distance": 4.0}]
    result = rank_by_distance(items, top_k=3)
    print("Test 9 - Full ordering:", [i["id"] for i in result])
    assert [i["id"] for i in result] == [2, 3, 1]


def test_rank_by_distance_never_compares_dicts():
    """Equal distances must not fall through to comparing the dicts.

    rank_hospitals needs a name in its tuple to avoid exactly this;
    rank_by_distance uses key= instead, so the dicts are never compared to each
    other and no TypeError can occur.
    """
    items = [{"id": 1, "distance": 2.0}, {"id": 2, "distance": 2.0}]
    result = rank_by_distance(items, top_k=2)
    print("Test 10 - Tied distances:", [i["id"] for i in result])
    assert len(result) == 2


if __name__ == "__main__":
    test_basic_ranking()
    test_excludes_zero_beds()
    test_top_k_larger_than_list()
    test_empty_list()
    test_all_zero_beds()
    test_rank_by_distance_picks_nearest()
    test_rank_by_distance_empty()
    test_rank_by_distance_top_k_larger_than_list()
    test_rank_by_distance_orders_all()
    test_rank_by_distance_never_compares_dicts()
    print("\nAll heap ranking tests passed.")