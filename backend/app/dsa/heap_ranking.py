import heapq

# How much extra travel a completely full hospital is treated as being worth.
#
# Distance is in kilometres and bed availability is a ratio, so they cannot be
# added directly. This constant converts capacity into KILOMETRE EQUIVALENT:
# a hospital with no spare capacity is ranked as if it were this much further
# away than it really is.
#
# The value is a judgement call, and it is the honest answer to "how much extra
# travel is a free bed worth?". At 2 km, capacity breaks ties between hospitals
# of similar distance but never overrides a hospital that is genuinely far
# closer, which is the behaviour we want: a dying patient should not be driven
# past a near hospital to reach an emptier one.
CAPACITY_PENALTY_KM = 2.0


def hospital_score(distance_km, available_beds, total_beds,
                   capacity_penalty_km=CAPACITY_PENALTY_KM):
    """Combined ranking key. LOWER is better.

        score = distance + penalty * (fraction of the hospital that is FULL)

    An empty hospital pays no penalty. A hospital down to its last bed pays
    almost the whole penalty. Both terms are in kilometres, so the sum means
    something.

    If total_beds is missing or zero the capacity of the hospital is unknown,
    so no penalty is applied and the ranking falls back to pure distance.
    """
    if not total_beds or total_beds <= 0:
        return distance_km

    free_fraction = max(0.0, min(1.0, available_beds / total_beds))
    return distance_km + capacity_penalty_km * (1.0 - free_fraction)


def rank_hospitals(hospitals, top_k=3, capacity_penalty_km=CAPACITY_PENALTY_KM):
    """Rank hospitals by distance AND availability, nearest-and-emptiest first.

    hospitals: dicts with "distance", "available_beds", "name", and ideally
    "total_beds" (without it the capacity term is skipped).

    Hospitals with no free beds are dropped before scoring: a hospital that
    cannot take the patient at all is not a candidate at any distance. That is
    a hard filter; capacity beyond that is a soft preference in the score.
    """
    heap = []
    for h in hospitals:
        if h["available_beds"] <= 0:
            continue
        score = hospital_score(h["distance"], h["available_beds"],
                               h.get("total_beds"), capacity_penalty_km)
        # Keep the score on the dict so the API can show why this hospital won.
        h["score"] = round(score, 3)
        heapq.heappush(heap, (score, h["name"], h))

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
