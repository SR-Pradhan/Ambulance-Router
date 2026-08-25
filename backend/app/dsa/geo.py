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


def interpolate_point(lat1, lng1, lat2, lng2, fraction):
    """A point `fraction` of the way from (lat1,lng1) to (lat2,lng2).

    Straight linear interpolation on the raw coordinates. Over a few km that is
    visually indistinguishable from a proper great-circle interpolation, and it
    is far easier to explain. Over hundreds of km it would drift.
    """
    fraction = max(0.0, min(1.0, fraction))
    return (
        lat1 + (lat2 - lat1) * fraction,
        lng1 + (lng2 - lng1) * fraction,
    )


def position_along_path(path_coords, distance_km):
    """Where you are after travelling `distance_km` along a path.

    path_coords is an ordered list of (lat, lng) waypoints. Walks segment by
    segment, subtracting each segment's length, until the remaining distance
    falls inside a segment -- then interpolates within it.

    Returns (lat, lng, travelled_km, total_km, finished).
    Clamps at both ends: negative distance gives the start, overshooting gives
    the end with finished=True.
    """
    if not path_coords:
        return None

    if len(path_coords) == 1:
        lat, lng = path_coords[0]
        return (lat, lng, 0.0, 0.0, True)

    # Length of each segment, and the total.
    segments = []
    total = 0.0
    for (a_lat, a_lng), (b_lat, b_lng) in zip(path_coords, path_coords[1:]):
        d = haversine_km(a_lat, a_lng, b_lat, b_lng)
        segments.append(d)
        total += d

    if distance_km <= 0:
        lat, lng = path_coords[0]
        return (lat, lng, 0.0, total, False)

    if distance_km >= total:
        lat, lng = path_coords[-1]
        return (lat, lng, total, total, True)

    remaining = distance_km
    for i, seg_len in enumerate(segments):
        if remaining <= seg_len:
            a_lat, a_lng = path_coords[i]
            b_lat, b_lng = path_coords[i + 1]
            # seg_len can only be 0 if two waypoints coincide; guard the divide.
            fraction = (remaining / seg_len) if seg_len > 0 else 0.0
            lat, lng = interpolate_point(a_lat, a_lng, b_lat, b_lng, fraction)
            return (lat, lng, distance_km, total, False)
        remaining -= seg_len

    lat, lng = path_coords[-1]
    return (lat, lng, total, total, True)
