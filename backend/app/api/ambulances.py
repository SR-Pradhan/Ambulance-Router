from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.models import Ambulance, Hospital, EmergencyRequest
from app.graph_loader import load_road_network, path_to_coords, path_length_km
from app.dsa.dijkstra import dijkstra
from app.dsa.geo import snap_to_node, position_along_path
from app.api.requests import dispatch_waiting, prune_completed

router = APIRouter()

# Same assumed speed as the dispatch logic.
AVG_AMBULANCE_SPEED_KMH = 40.0

# Ambulances move this many times faster than real time.
#
# This is PURELY a demo convenience: at 1x, a 12-minute journey takes 12 real
# minutes to watch, which is useless in a live demonstration.
#
# It was 60x, which turned out to be too fast to SEE. Journeys on this network
# are short (a few km, so two to eight simulated minutes), and at 60x that is a
# two to eight second trip: by the time you look at the map the ambulance has
# already arrived. At 10x the same journey takes half a minute or so, which is
# long enough to watch it cross the map and short enough to hold attention.
# It is a simulation artifact, not a claim about real ambulances, which is why
# the API returns it explicitly.
SIMULATION_TIME_MULTIPLIER = 10.0


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



def sweep_arrived(db, graph, coords, now):
    """Complete any trip whose ambulance has already reached the hospital.

    THIS FIXES A DEMO-KILLING BUG. Positions are a pure function of
    `created_at`, so a request made ten minutes ago has notionally travelled
    400 km at the 60x simulation speed: it is parked at the hospital, finished,
    forever. Nothing ever marked it complete, because completion was only ever
    triggered by an admin clicking a button. So every dispatch permanently
    consumed an ambulance, exactly as the docstring on complete_request warns.

    Left alone the fleet drains to zero and the demo shows three symptoms that
    look like three separate bugs but are all this one:

      1. "the ambulance is not moving"  - it is finished, frozen at 100%
      2. "no route to the patient"      - no ambulance was free to assign, so
                                          there is no pickup leg to draw
      3. "every request has the same route" - the only journeys left on the map
                                          are the same few frozen ones

    Completing on arrival is the simulation advancing, not an administrative
    act, so it is deliberately NOT behind the admin key. The manual Complete
    button still exists for ending a trip early.

    Returns (completed_ids, dispatched_ids).
    """
    active = db.query(EmergencyRequest).filter(
        EmergencyRequest.status == "en_route",
        EmergencyRequest.assigned_ambulance_id.isnot(None),
    ).all()

    # Reconcile orphans first.
    #
    # An ambulance flagged busy that no en_route request refers to is stranded:
    # nothing will ever free it, because every release path keys off a request.
    # One leaked vehicle permanently removes a third of a three-ambulance
    # fleet, which is the same failure as the bug this sweep exists to fix,
    # just slower. Rather than hunt every path that could leak one, the
    # invariant is asserted here on every poll: busy means a live trip.
    on_trip = {r.assigned_ambulance_id for r in active}
    orphans = [
        a for a in db.query(Ambulance).filter(Ambulance.status == "busy").all()
        if a.id not in on_trip
    ]
    for vehicle in orphans:
        vehicle.status = "available"
    if orphans:
        db.commit()

    completed = []

    for req in active:
        started = req.dispatched_at or req.created_at
        if started is None:
            continue
        ambulance = db.query(Ambulance).filter(
            Ambulance.id == req.assigned_ambulance_id
        ).first()
        hospital = db.query(Hospital).filter(
            Hospital.id == req.assigned_hospital_id
        ).first()
        if ambulance is None or hospital is None:
            continue

        journey, _pickup_km, _transport_km, _idx = _journey_coords(
            db, graph, coords, req, ambulance, hospital
        )
        if not journey:
            continue

        elapsed_hours = (now - started).total_seconds() / 3600.0
        travelled = max(0.0, elapsed_hours * AVG_AMBULANCE_SPEED_KMH
                        * SIMULATION_TIME_MULTIPLIER)
        _lat, _lng, _done_km, _total_km, finished = position_along_path(
            journey, travelled
        )
        if not finished:
            continue

        # Park the vehicle where it actually ended up, so the next dispatch
        # measures from its real position. Same reasoning as complete_request.
        ambulance.current_lat = hospital.latitude
        ambulance.current_lng = hospital.longitude
        ambulance.status = "available"
        req.status = "completed"
        completed.append(req.id)

    if not completed and not orphans:
        return [], []

    if completed:
        db.commit()

    # Ambulances just became free, so hand them to the most urgent waiting
    # patients. This is what keeps the triage queue draining instead of
    # growing without bound.
    dispatched = [r.id for r in dispatch_waiting(db)]

    # Only worth checking when something actually finished, which is the only
    # moment the completed count can have grown.
    if completed:
        prune_completed(db)

    return completed, dispatched


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

    # Advance the simulation before reporting on it: retire arrived trips and
    # hand the freed ambulances to the queue. This endpoint is polled every two
    # seconds by any open tab, so it is the closest thing the system has to a
    # clock. It does mean a GET writes state, which is a genuine compromise;
    # the alternative is a background worker, and the whole live-tracking
    # design exists specifically to avoid needing one.
    swept, dispatched = sweep_arrived(db, graph, coords, now)

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
        # Falls back to created_at only for rows predating the dispatched_at
        # column, so old data still renders instead of vanishing.
        started = req.dispatched_at or req.created_at
        if ambulance is None or hospital is None or started is None:
            continue

        journey, pickup_km, transport_km, pickup_index = _journey_coords(
            db, graph, coords, req, ambulance, hospital
        )
        if not journey:
            continue

        elapsed_hours = (now - started).total_seconds() / 3600.0
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
        "just_completed": swept,
        "just_dispatched": dispatched,
        "ambulances": live + idle,
    }
