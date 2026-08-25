import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))

from dsa.heap_ranking import (rank_hospitals, rank_by_distance,
                              hospital_score, CAPACITY_PENALTY_KM)


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


# --- ranking by distance AND availability (v1.5) ----------------------------

def test_emptier_hospital_can_beat_a_closer_one():
    """The whole point of scoring on availability.

    Two hospitals a short distance apart: the nearer one is nearly full, the
    slightly further one is nearly empty. The emptier one must win, because the
    capacity penalty outweighs the small distance difference.
    """
    hospitals = [
        {"name": "Nearly full", "distance": 4.0, "available_beds": 1, "total_beds": 50},
        {"name": "Nearly empty", "distance": 4.9, "available_beds": 48, "total_beds": 50},
    ]
    result = rank_hospitals(hospitals, top_k=2)
    print(f"Test 11 - Full 4.0km scores {hospitals[0]['score']}, "
          f"empty 4.9km scores {hospitals[1]['score']} -> "
          f"{[h['name'] for h in result]}")
    assert result[0]["name"] == "Nearly empty"


def test_distance_still_dominates_when_the_gap_is_large():
    """Capacity must not override a hospital that is genuinely much closer.

    The penalty is capped at CAPACITY_PENALTY_KM, so it can never move a
    hospital more than that many kilometres in the ranking.
    """
    hospitals = [
        {"name": "Close and full", "distance": 2.0, "available_beds": 1, "total_beds": 50},
        {"name": "Far and empty", "distance": 9.0, "available_beds": 50, "total_beds": 50},
    ]
    result = rank_hospitals(hospitals, top_k=2)
    print("Test 12 - Large distance gap:", [h["name"] for h in result])
    assert result[0]["name"] == "Close and full"


def test_same_distance_prefers_more_capacity():
    hospitals = [
        {"name": "Tight", "distance": 5.0, "available_beds": 2, "total_beds": 40},
        {"name": "Roomy", "distance": 5.0, "available_beds": 30, "total_beds": 40},
    ]
    result = rank_hospitals(hospitals, top_k=2)
    print("Test 13 - Same distance:", [h["name"] for h in result])
    assert result[0]["name"] == "Roomy"


def test_full_hospital_still_excluded_entirely():
    """Capacity is a soft preference, but ZERO beds is still a hard filter."""
    hospitals = [
        {"name": "Full", "distance": 0.1, "available_beds": 0, "total_beds": 50},
        {"name": "Open", "distance": 20.0, "available_beds": 5, "total_beds": 50},
    ]
    result = rank_hospitals(hospitals, top_k=2)
    print("Test 14 - Zero beds excluded:", [h["name"] for h in result])
    assert len(result) == 1 and result[0]["name"] == "Open"


def test_penalty_is_bounded():
    """An empty hospital pays nothing; a hospital on its last bed pays almost
    the full penalty. Nothing pays more."""
    empty = hospital_score(5.0, 50, 50)
    last_bed = hospital_score(5.0, 1, 50)
    print(f"Test 15 - Empty scores {empty}, last bed scores {last_bed:.3f}, "
          f"penalty cap {CAPACITY_PENALTY_KM}")
    assert empty == 5.0
    assert last_bed < 5.0 + CAPACITY_PENALTY_KM
    assert last_bed > 5.0 + CAPACITY_PENALTY_KM * 0.9


def test_missing_total_beds_falls_back_to_distance():
    """Older callers that do not supply total_beds must still work."""
    assert hospital_score(7.5, 3, None) == 7.5
    assert hospital_score(7.5, 3, 0) == 7.5
    print("Test 16 - Unknown capacity falls back to pure distance: 7.5")


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
    test_emptier_hospital_can_beat_a_closer_one()
    test_distance_still_dominates_when_the_gap_is_large()
    test_same_distance_prefers_more_capacity()
    test_full_hospital_still_excluded_entirely()
    test_penalty_is_bounded()
    test_missing_total_beds_falls_back_to_distance()
    print("\nAll heap ranking tests passed.")