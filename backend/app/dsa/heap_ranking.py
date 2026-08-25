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