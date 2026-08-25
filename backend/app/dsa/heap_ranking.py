import heapq

def rank_hospitals(hospitals, top_k=3):
    # hospitals: list of dicts like {"name": "X", "distance": 4.2, "available_beds": 3}
    heap = []
    for h in hospitals:
        if h["available_beds"] <= 0:
            continue
        heapq.heappush(heap, (h["distance"], h["name"], h))

    result = []
    for _ in range(min(top_k, len(heap))):
        _, _, h = heapq.heappop(heap)
        result.append(h)
    return result

def rank_by_distance(items, top_k=1):
    """Return the top_k items with the smallest "distance", nearest first.

    A generic sibling of rank_hospitals() above: no beds, no domain rules, just
    distance. Used for picking the nearest available ambulance.

    heapq.nsmallest is O(n) for small k, versus O(n log n) for pushing every
    item onto a heap one at a time. For k=1 -- the ambulance case -- that is the
    right tool: we want a single minimum, not a fully ordered list.

    Using key= also sidesteps the tuple tie-breaker that rank_hospitals needs:
    nothing is compared except the distance, so the dicts are never compared to
    each other and cannot raise TypeError.
    """
    if not items:
        return []
    return heapq.nsmallest(top_k, items, key=lambda x: x["distance"])
