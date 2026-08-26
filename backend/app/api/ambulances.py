from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.models import Ambulance, Hospital, EmergencyRequest
from app.graph_loader import load_road_network, path_to_coords, path_length_km
from app.dsa.dijkstra import dijkstra
from app.dsa.geo import snap_to_node, position_along_path

router = APIRouter()

# Same assumed speed as the dispatch logic.
AVG_AMBULANCE_SPEED_KMH = 40.0

# Ambulances move this many times faster than real time.
#
# This is PURELY a demo convenience: at 1x, a 12-minute journey takes 12 real
# minutes to watch, which is useless in a live demonstration. At 60x the same
# journey completes in about 12 seconds, so the map visibly animates while
# someone is looking at it. It is a simulation artifact, not a claim about
# real ambulances -- which is why the API returns it explicitly.
SIMULATION_TIME_MULTIPLIER = 60.0


def _journey_coords(db, graph, coords, request, ambulance, hospital):
    """The full route an ambulance drives for one request, as waypoints.

    Two legs: ambulance -> patient (pickup), then patient -> hospital
    (transport). Returned as one continuous list of (lat, lng), plus the length
    of the pickup leg so we can tell which phase the ambulance is in.

    The route is recomputed rather than read from storage because
    emergency_requests has no columns for it -- the same trade-off documented
    on GET /requests/{id}.
    """
    a_node, _ = snap_to_node(ambulance.current_lat, ambulance.current_lng, coords)
    p_node, _ = snap_to_node(request.patient_lat, request.patient_lng, coords)
    h_node, _ = snap_to_node(hospital.latitude, hospital.longitude, coords)

    # dijkstra returns MINUTES since v1.7, so the physical distances have to be
    # measured from the path itself. Position interpolation works in kilometres
    # (it walks real coordinates), so mixing the two up would put ambulances in
    # the wrong place entirely.
    pickup_path, _pickup_minutes = dijkstra(graph, a_node, p_node)
    transport_path, _transport_minutes = dijkstra(graph, p_node, h_node)

    if pickup_path is None or transport_path is None:
        return None, 0.0, 0.0, 0

    pickup_km = path_length_km(pickup_path, coords)
    transport_km = path_length_km(transport_path, coords)

    pickup_coords = path_to_coords(pickup_path, coords)
    transport_coords = path_to_coords(transport_path, coords)

    # Drop the first transport waypoint: it is the patient node, already the
    # last waypoint of the pickup leg. Keeping it would add a zero-length
    # segment and make the two legs look discontinuous.
    full = pickup_coords + transport_coords[1:]

    # Index of the patient in the combined path. The two legs are drawn in
    # different colours on the map, so the frontend has to know exactly where
    # one ends and the other begins. Deriving it there (nearest waypoint to the
    # patient) would be a guess; this is exact.
    pickup_index = max(0, len(pickup_coords) - 1)

    return full, pickup_km, transport_km, pickup_index


@router.get("/ambulances")
def list_ambulances(db: Session = Depends(get_db)):
    """All ambulances with their home position and status."""
    # Ordered for the same reason as /hospitals: completing a trip UPDATEs the
    # ambulance row, which would otherwise reorder the list.
    ambulances = db.query(Ambulance).order_by(Ambulance.id).all()
    return {
        "count": len(ambulances),
        "available": sum(1 for a in ambulances if a.status == "available"),
        "busy": sum(1 for a in ambulances if a.status == "busy"),
        "ambulances": [
            {
                "id": a.id,
                "current_lat": a.current_lat,
                "current_lng": a.current_lng,
                "status": a.status,
            }
            for a in ambulances
        ],
    }


@router.get("/ambulances/live")
def live_ambulances(db: Session = Depends(get_db)):
    """Simulated live positions.

    An ambulance's position is a pure function of how long ago its request was
    created: travelled = elapsed * speed * multiplier, then walk that far along
    the route. Nothing runs in the background and no state is written, so the
    answer is consistent on every refresh and survives a server restart.
    """
    now = datetime.now()
    graph, coords = load_road_network(db)

    # Only requests that are actually under way have a moving ambulance.
    active = db.query(EmergencyRequest).filter(
        EmergencyRequest.status == "en_route",
        EmergencyRequest.assigned_ambulance_id.isnot(None),
    ).all()

    moving_ids = set()
    live = []

    for req in active:
        ambulance = db.query(Ambulance).filter(
            Ambulance.id == req.assigned_ambulance_id
        ).first()
        hospital = db.query(Hospital).filter(
            Hospital.id == req.assigned_hospital_id
        ).first()
        if ambulance is None or hospital is None or req.created_at is None:
            continue

        journey, pickup_km, transport_km, pickup_index = _journey_coords(
            db, graph, coords, req, ambulance, hospital
        )
        if not journey:
            continue

        elapsed_hours = (now - req.created_at).total_seconds() / 3600.0
        travelled = max(0.0, elapsed_hours * AVG_AMBULANCE_SPEED_KMH
                        * SIMULATION_TIME_MULTIPLIER)

        lat, lng, travelled_km, total_km, finished = position_along_path(
            journey, travelled
        )

        if finished:
            phase = "arrived"
        elif travelled_km < pickup_km:
            phase = "to_patient"
        else:
            phase = "to_hospital"

        remaining_km = max(0.0, total_km - travelled_km)
        moving_ids.add(ambulance.id)

        live.append({
            "ambulance_id": ambulance.id,
            "request_id": req.id,
            "lat": round(lat, 6),
            "lng": round(lng, 6),
            "phase": phase,
            "travelled_km": round(travelled_km, 3),
            "total_km": round(total_km, 3),
            "progress_percent": round(
                (travelled_km / total_km * 100) if total_km > 0 else 100.0, 1
            ),
            "remaining_minutes": round(
                remaining_km / AVG_AMBULANCE_SPEED_KMH * 60, 1
            ),
            "patient": {"lat": req.patient_lat, "lng": req.patient_lng},
            "hospital": {"id": hospital.id, "name": hospital.name,
                         "lat": hospital.latitude, "lng": hospital.longitude},
            "route": [{"lat": round(la, 6), "lng": round(ln, 6)}
                      for la, ln in journey],
            # Where the pickup leg ends and the hospital leg begins.
            "pickup_index": pickup_index,
        })

    # Everything else is parked at its home position.
    idle = [
        {
            "ambulance_id": a.id,
            "request_id": None,
            "lat": a.current_lat,
            "lng": a.current_lng,
            "phase": "idle" if a.status == "available" else "busy_unassigned",
            "progress_percent": None,
            "route": [],
        }
        for a in db.query(Ambulance).order_by(Ambulance.id).all()
        if a.id not in moving_ids
    ]

    return {
        "server_time": now.isoformat(),
        "simulation": {
            "speed_kmh": AVG_AMBULANCE_SPEED_KMH,
            "time_multiplier": SIMULATION_TIME_MULTIPLIER,
            "note": "Positions are simulated by interpolating along the "
                    "computed route from the request's created_at. No real GPS.",
        },
        "moving": len(live),
        "ambulances": live + idle,
    }
