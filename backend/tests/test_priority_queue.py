import sys
import os
import random
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))

from dsa.priority_queue import (PriorityQueue, triage_score,
                                SEVERITY_RANK, AGING_MINUTES_PER_LEVEL)


def test_pops_in_priority_order():
    pq = PriorityQueue()
    for pri, name in [(2, "standard"), (0, "critical"), (1, "urgent")]:
        pq.push(pri, name, {"name": name})

    order = [p["name"] for p in pq.drain()]
    print("Test 1 - Priority order:", order)
    assert order == ["critical", "urgent", "standard"]


def test_empty_queue_behaviour():
    pq = PriorityQueue()
    print("Test 2 - Empty:", len(pq), pq.is_empty())
    assert pq.is_empty() and len(pq) == 0
    for method in (pq.pop, pq.peek):
        try:
            method()
            raise AssertionError(f"{method.__name__} on empty queue should raise")
        except IndexError:
            pass


def test_equal_priority_is_fifo():
    """Equal-priority patients must be served in arrival order, not randomly."""
    pq = PriorityQueue()
    for request_id in [7, 3, 5, 1]:
        pq.push(1.0, request_id, {"id": request_id})

    order = [p["id"] for p in pq.drain()]
    print("Test 3 - Tie-break by id:", order)
    assert order == [1, 3, 5, 7]


def test_never_compares_payloads():
    """Dicts are not orderable; the tiebreak must stop Python ever reaching them."""
    pq = PriorityQueue()
    pq.push(1.0, 1, {"a": 1})
    pq.push(1.0, 2, {"b": 2})   # same priority, different dicts
    result = pq.drain()
    print("Test 4 - Equal priority with dict payloads:", result)
    assert len(result) == 2


def test_heap_property_against_sorted():
    """Fuzz it: whatever goes in, it must come out sorted."""
    random.seed(42)
    for trial in range(30):
        values = [random.uniform(-5, 5) for _ in range(random.randint(1, 40))]
        pq = PriorityQueue()
        for i, v in enumerate(values):
            pq.push(v, i, v)
        popped = pq.drain()
        assert popped == sorted(values), f"Trial {trial} broke the heap property"
    print("Test 5 - Fuzz vs sorted(): 30 random trials all correct")


def test_peek_does_not_remove():
    pq = PriorityQueue()
    pq.push(5, 1, "five")
    pq.push(2, 2, "two")
    print("Test 6 - Peek:", pq.peek(), "len still", len(pq))
    assert pq.peek() == "two"
    assert len(pq) == 2


# --- triage scoring ---------------------------------------------------------

def test_severity_orders_fresh_requests():
    fresh = {s: triage_score(s, 0) for s in SEVERITY_RANK}
    print("Test 7 - Fresh scores:", fresh)
    assert fresh["critical"] < fresh["urgent"] < fresh["standard"]


def test_waiting_improves_priority():
    early = triage_score("standard", 0)
    later = triage_score("standard", 15)
    print(f"Test 8 - Standard: fresh {early}, after 15 min {later}")
    assert later < early, "Waiting must improve priority"


def test_aging_prevents_starvation():
    """The whole point of aging.

    A standard patient who has waited long enough must eventually outrank a
    critical patient who just walked in -- otherwise a steady stream of
    critical cases starves them forever.
    """
    waited = AGING_MINUTES_PER_LEVEL * 2 + 1   # just over two full levels
    old_standard = triage_score("standard", waited)
    fresh_critical = triage_score("critical", 0)

    print(f"Test 9 - Standard waiting {waited} min scores {old_standard:.2f}; "
          f"fresh critical scores {fresh_critical:.2f}")
    assert old_standard < fresh_critical, "Aging failed - standard would starve"


def test_critical_still_beats_standard_early_on():
    """Aging must not be so aggressive that severity stops mattering."""
    fresh_critical = triage_score("critical", 0)
    standard_5min = triage_score("standard", 5)
    print(f"Test 10 - Critical {fresh_critical:.2f} vs standard waiting 5 min "
          f"{standard_5min:.2f}")
    assert fresh_critical < standard_5min


def test_unknown_severity_falls_back_to_standard():
    print("Test 11 - Unknown severity:", triage_score("banana", 0))
    assert triage_score("banana", 0) == triage_score("standard", 0)


def test_end_to_end_triage_ordering():
    """The realistic case: a queue mixing severities and wait times."""
    waiting = [
        {"id": 1, "severity": "standard", "waited": 45},   # waited a long time
        {"id": 2, "severity": "critical", "waited": 0},    # just arrived
        {"id": 3, "severity": "urgent", "waited": 2},
        {"id": 4, "severity": "standard", "waited": 0},
    ]
    pq = PriorityQueue()
    for w in waiting:
        pq.push(triage_score(w["severity"], w["waited"]), w["id"], w)

    order = [w["id"] for w in pq.drain()]
    print("Test 12 - Realistic queue order:", order)
    # #1 has waited 45 min (score 2 - 4.5 = -2.5) so it now outranks even the
    # fresh critical (score 0). #4 just arrived and goes last.
    assert order[0] == 1
    assert order[-1] == 4


if __name__ == "__main__":
    test_pops_in_priority_order()
    test_empty_queue_behaviour()
    test_equal_priority_is_fifo()
    test_never_compares_payloads()
    test_heap_property_against_sorted()
    test_peek_does_not_remove()
    test_severity_orders_fresh_requests()
    test_waiting_improves_priority()
    test_aging_prevents_starvation()
    test_critical_still_beats_standard_early_on()
    test_unknown_severity_falls_back_to_standard()
    test_end_to_end_triage_ordering()
    print("\nAll priority queue tests passed.")
