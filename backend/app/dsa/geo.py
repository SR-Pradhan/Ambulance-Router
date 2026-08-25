import math

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle distance in km between two lat/lng points.

    Pure function - no DB, no FastAPI. Used to turn hospital coordinates
    into a real distance the heap can rank on.
    """
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)

    a = math.sin(d_lat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d_lng / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return EARTH_RADIUS_KM * c


def snap_to_node(lat, lng, node_coords):
    """Find the road node closest to a coordinate.

    Patients and hospitals are stored as lat/lng, but Dijkstra works in node
    ids -- this is the bridge between the two. node_coords maps
    {node_id: (lat, lng)}.

    Returns (node_id, distance_km), or (None, inf) if there are no nodes.

    Linear scan, O(n). Fine at this scale; a real system would use a spatial
    index (PostGIS, or a k-d tree) so it doesn't check every node.
    """
    best_node = None
    best_dist = float('inf')

    for node_id, (n_lat, n_lng) in node_coords.items():
        d = haversine_km(lat, lng, n_lat, n_lng)
        if d < best_dist:
            best_node = node_id
            best_dist = d

    return best_node, best_dist
