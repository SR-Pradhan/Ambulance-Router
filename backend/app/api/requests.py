from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.models import Hospital, Ambulance, EmergencyRequest
from app.graph_loader import load_road_network
from app.schemas.requests import EmergencyRequestCreate
from app.dsa.dijkstra import dijkstra_all, reconstruct_path
from app.dsa.geo import snap_to_node
from app.dsa.heap_ranking import rank_hospitals, rank_by_distance
from app.dsa.priority_queue import PriorityQueue, triage_score

router = APIRouter()

# Assumed average ambulance speed. This is a SIMPLIFICATION: there is no live
# traffic data in this project, so ETA is just distance / speed. A real system
# would use time-of-day traffic, road types and priority-vehicle rules.
AVG_AMBULANCE_SPEED_KMH = 40.0


def compute_best_route(db: Session, patient_lat: float, patient_lng: float):
    """Pick the best hospital for a patient and route to it.

    This is where the two halves of the project finally meet: the heap picks
    the hospital, Dijkstra finds the road route. Ranking is on ROAD distance,
    not straight-line -- which is the whole point of this version.

    Returns a result dict, or None if no hospital with free beds is reachable.
    """
    # 1. Load the road network (shared loader - see app/graph_loader.py).
    graph, coords = load_road_network(db)

    if not coords:
        return None

    # 2. The patient gave us a coordinate; Dijkstra needs a node.
    patient_node, patient_offset = snap_to_node(patient_lat, patient_lng, coords)

    # 3. ONE Dijkstra run gives the distance to every node, and therefore to
    #    every hospital. Running it once per hospital would repeat this work.
    distances, prev = dijkstra_all(graph, patient_node)

    # 4. Build the candidate list, measured by road distance.
    candidates = []
    for h in db.query(Hospital).all():
        if h.available_beds <= 0:
            continue  # full - the heap would drop it anyway, but skip the work

        h_node, h_offset = snap_to_node(h.latitude, h.longitude, coords)
        road_km = distances.get(h_node, float('inf'))
        if road_km == float('inf'):
            continue  # unreachable from the patient (e.g. disconnected road)

        candidates.append({
            "id": h.id,
            "name": h.name,
            "latitude": h.latitude,
            "longitude": h.longitude,
            "available_beds": h.available_beds,
            "total_beds": h.total_beds,
            "node_id": h_node,
            "distance": round(road_km, 3),      # key the heap ranks on
            "distance_type": "road",
        })

    if not candidates:
        return None

    # 5. The heap picks the winner. rank_hospitals doesn't know or care that
    #    "distance" is now road distance rather than straight-line.
    ranked = rank_hospitals(candidates, top_k=len(candidates))
    best = ranked[0]

    # 6. The actual route to the winner, and how long it should take.
    path = reconstruct_path(prev, patient_node, best["node_id"])
    eta_minutes = round(best["distance"] / AVG_AMBULANCE_SPEED_KMH * 60, 1)

    # 7. Nearest AVAILABLE ambulance to the patient.
    #    We reuse the very same `distances` map computed above. That works
    #    because Graph.add_edge inserts both directions, so the graph is
    #    undirected and distance(patient -> ambulance) equals
    #    distance(ambulance -> patient). No second Dijkstra run is needed.
    ambulance_candidates = []
    for a in db.query(Ambulance).all():
        if a.status != "available":
            continue
        a_node, _ = snap_to_node(a.current_lat, a.current_lng, coords)
        pickup_km = distances.get(a_node, float('inf'))
        if pickup_km == float('inf'):
            continue
        ambulance_candidates.append({
            "id": a.id,
            "current_lat": a.current_lat,
            "current_lng": a.current_lng,
            "node_id": a_node,
            "distance": round(pickup_km, 3),
        })

    nearest = rank_by_distance(ambulance_candidates, top_k=1)
    ambulance = nearest[0] if nearest else None

    if ambulance is not None:
        ambulance["pickup_path"] = reconstruct_path(
            prev, patient_node, ambulance["node_id"]
        )
        ambulance["pickup_eta_minutes"] = round(
            ambulance["distance"] / AVG_AMBULANCE_SPEED_KMH * 60, 1
        )

    return {
        "patient": {
            "lat": patient_lat,
            "lng": patient_lng,
            "nearest_node": patient_node,
            "snap_distance_km": round(patient_offset, 3),
        },
        "hospital": best,
        "route": {
            "path": path,
            "distance_km": best["distance"],
            "eta_minutes": eta_minutes,
            "assumed_speed_kmh": AVG_AMBULANCE_SPEED_KMH,
        },
        "ambulance": ambulance,
        "total_eta_minutes": (
            round(ambulance["pickup_eta_minutes"] + eta_minutes, 1)
            if ambulance else None
        ),
        "alternatives": ranked[1:],
    }


def waiting_queue(db: Session, now=None):
    """Build the triage queue from every request still waiting for an ambulance.

    The queue is DERIVED from the database on demand, never stored. Same
    philosophy as live tracking: there is no long-lived in-memory heap to fall
    out of sync with the database, to lose on restart, or to corrupt if two
    workers disagree. Rebuilding costs O(n log n) on a handful of rows.

    Returns a PriorityQueue of request rows, most urgent first.
    """
    now = now or datetime.now()

    pending = db.query(EmergencyRequest).filter(
        EmergencyRequest.status == "pending",
        EmergencyRequest.assigned_ambulance_id.is_(None),
    ).all()

    pq = PriorityQueue()
    for req in pending:
        waited = ((now - req.created_at).total_seconds() / 60.0
                  if req.created_at else 0.0)
        # Tie-break on id so equal-priority patients keep arrival order.
        pq.push(triage_score(req.severity, waited), req.id, req)

    return pq


def dispatch_waiting(db: Session):
    """Give every free ambulance to the most urgent waiting patient.

    Called after a request is created AND after a trip completes, which is what
    makes the queue meaningful rather than decorative: when an ambulance frees
    up it goes to whoever needs it most, not to whoever asked first.

    Returns the list of requests that just got an ambulance.
    """
    queue = waiting_queue(db)
    dispatched = []

    while not queue.is_empty():
        # Any ambulance free? Re-checked each round because each assignment
        # consumes one.
        if not db.query(Ambulance).filter(Ambulance.status == "available").first():
            break

        req = queue.pop()
        result = compute_best_route(db, req.patient_lat, req.patient_lng)
        if result is None or result["ambulance"] is None:
            continue  # no reachable hospital with beds, or no usable ambulance

        vehicle = db.query(Ambulance).filter(
            Ambulance.id == result["ambulance"]["id"]
        ).first()
        if vehicle is None or vehicle.status != "available":
            continue

        req.assigned_hospital_id = result["hospital"]["id"]
        req.assigned_ambulance_id = vehicle.id
        req.status = "en_route"
        vehicle.status = "busy"
        dispatched.append(req)

    if dispatched:
        db.commit()
    return dispatched


@router.get("/queue")
def get_queue(db: Session = Depends(get_db)):
    """The triage queue right now, in the order patients will be served.

    Shows the score so the ordering is inspectable: severity sets the starting
    position and waiting drags it towards the front.
    """
    now = datetime.now()
    queue = waiting_queue(db, now)
    ordered = queue.drain()

    return {
        "waiting": len(ordered),
        "aging_minutes_per_level": 10.0,
        "queue": [
            {
                "position": i + 1,
                "request_id": r.id,
                "severity": r.severity,
                "waited_minutes": round(
                    (now - r.created_at).total_seconds() / 60.0, 1
                ) if r.created_at else 0.0,
                "score": round(triage_score(
                    r.severity,
                    (now - r.created_at).total_seconds() / 60.0 if r.created_at else 0.0
                ), 3),
                "patient_lat": r.patient_lat,
                "patient_lng": r.patient_lng,
            }
            for i, r in enumerate(ordered)
        ],
        "note": "Lower score is served first. Waiting lowers the score, so no "
                "patient can be starved by a stream of more urgent arrivals.",
    }


@router.post("/requests")
def create_request(payload: EmergencyRequestCreate, db: Session = Depends(get_db)):
    """Create an emergency request: choose a hospital, route to it, store it."""
    result = compute_best_route(db, payload.patient_lat, payload.patient_lng)

    if result is None:
        raise HTTPException(
            status_code=503,
            detail="No hospital with available beds is reachable from this location.",
        )

    # The request is created as PENDING and joins the triage queue. It does not
    # grab an ambulance directly -- dispatch_waiting decides who gets the next
    # free vehicle, so a critical patient already waiting is served before a
    # standard one that just arrived.
    emergency = EmergencyRequest(
        patient_lat=payload.patient_lat,
        patient_lng=payload.patient_lng,
        severity=payload.severity,
        assigned_hospital_id=result["hospital"]["id"],
        assigned_ambulance_id=None,
        status="pending",
    )
    db.add(emergency)
    db.commit()
    db.refresh(emergency)

    # Now run the queue. This may assign an ambulance to THIS request, or to a
    # more urgent one that was already waiting.
    dispatch_waiting(db)
    db.refresh(emergency)

    # Report what actually happened, not what compute_best_route proposed --
    # the queue may have given that ambulance to someone else.
    assigned = None
    if emergency.assigned_ambulance_id is not None:
        vehicle = db.query(Ambulance).filter(
            Ambulance.id == emergency.assigned_ambulance_id
        ).first()
        if vehicle:
            assigned = {
                "id": vehicle.id,
                "current_lat": vehicle.current_lat,
                "current_lng": vehicle.current_lng,
            }

    queued_ahead = [
        r.id for r in waiting_queue(db).drain() if r.id != emergency.id
    ] if emergency.status == "pending" else []

    return {
        "request_id": emergency.id,
        "status": emergency.status,
        "severity": emergency.severity,
        "created_at": emergency.created_at,
        **result,
        "ambulance": assigned,
        "queued_behind": queued_ahead,
        "total_eta_minutes": result["total_eta_minutes"] if assigned else None,
    }


@router.get("/requests/{request_id}")
def get_request(request_id: int, db: Session = Depends(get_db)):
    """Look up a stored request, with its route recalculated.

    The route is recomputed rather than read back, because emergency_requests
    has no columns for path or ETA -- only the chosen hospital is persisted.
    Storing the route would need a schema migration.
    """
    emergency = db.query(EmergencyRequest).filter(
        EmergencyRequest.id == request_id
    ).first()

    if emergency is None:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")

    hospital = db.query(Hospital).filter(
        Hospital.id == emergency.assigned_hospital_id
    ).first()

    result = compute_best_route(db, emergency.patient_lat, emergency.patient_lng)

    # Show the ambulance that was ACTUALLY assigned, read from the request --
    # not result["ambulance"]. That one is recomputed live, and since the
    # assigned vehicle is now "busy" it would report a different ambulance.
    vehicle = None
    if emergency.assigned_ambulance_id is not None:
        vehicle = db.query(Ambulance).filter(
            Ambulance.id == emergency.assigned_ambulance_id
        ).first()

    return {
        "request_id": emergency.id,
        "status": emergency.status,
        "created_at": emergency.created_at,
        "patient_lat": emergency.patient_lat,
        "patient_lng": emergency.patient_lng,
        "assigned_hospital_id": emergency.assigned_hospital_id,
        "assigned_hospital_name": hospital.name if hospital else None,
        "assigned_ambulance_id": emergency.assigned_ambulance_id,
        "assigned_ambulance": {
            "id": vehicle.id,
            "current_lat": vehicle.current_lat,
            "current_lng": vehicle.current_lng,
            "status": vehicle.status,
        } if vehicle else None,
        "route": result["route"] if result else None,
    }


@router.get("/requests")
def list_requests(db: Session = Depends(get_db)):
    """Every emergency request, newest first. Feeds the admin dashboard."""
    rows = db.query(EmergencyRequest).order_by(EmergencyRequest.id.desc()).all()
    hospitals = {h.id: h.name for h in db.query(Hospital).all()}

    return {
        "count": len(rows),
        "by_status": {
            status: sum(1 for r in rows if r.status == status)
            for status in ("pending", "en_route", "completed")
        },
        "requests": [
            {
                "id": r.id,
                "patient_lat": r.patient_lat,
                "patient_lng": r.patient_lng,
                "status": r.status,
                "severity": r.severity,
                "assigned_hospital_id": r.assigned_hospital_id,
                "assigned_hospital_name": hospitals.get(r.assigned_hospital_id),
                "assigned_ambulance_id": r.assigned_ambulance_id,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }


@router.patch("/requests/{request_id}/complete")
def complete_request(request_id: int, db: Session = Depends(get_db)):
    """Finish a trip: free the ambulance and park it at the hospital.

    This closes the loop. Before it existed, every dispatch permanently consumed
    an ambulance and the pool drained to nothing after two requests.

    Moving the ambulance to the hospital is deliberate, not cosmetic: it is
    genuinely where the vehicle ends up, so the next dispatch measures distance
    from its real position rather than from a stale depot.

    Idempotent -- completing an already-completed request is a no-op, not an
    error, so a double-clicked dashboard button cannot corrupt anything.
    """
    emergency = db.query(EmergencyRequest).filter(
        EmergencyRequest.id == request_id
    ).first()
    if emergency is None:
        raise HTTPException(status_code=404,
                            detail=f"Request {request_id} not found")

    if emergency.status == "completed":
        return {
            "request_id": emergency.id,
            "status": emergency.status,
            "changed": False,
            "detail": "Request was already completed.",
        }

    freed_ambulance = None
    if emergency.assigned_ambulance_id is not None:
        vehicle = db.query(Ambulance).filter(
            Ambulance.id == emergency.assigned_ambulance_id
        ).first()
        if vehicle:
            hospital = db.query(Hospital).filter(
                Hospital.id == emergency.assigned_hospital_id
            ).first()
            if hospital:
                vehicle.current_lat = hospital.latitude
                vehicle.current_lng = hospital.longitude
            vehicle.status = "available"
            freed_ambulance = {
                "id": vehicle.id,
                "status": vehicle.status,
                "current_lat": vehicle.current_lat,
                "current_lng": vehicle.current_lng,
            }

    emergency.status = "completed"
    db.commit()
    db.refresh(emergency)

    # An ambulance just became free -- hand it to the most urgent waiting
    # patient. This is where the priority queue earns its place.
    newly_dispatched = [
        {"request_id": r.id, "severity": r.severity,
         "assigned_ambulance_id": r.assigned_ambulance_id}
        for r in dispatch_waiting(db)
    ]

    return {
        "request_id": emergency.id,
        "status": emergency.status,
        "changed": True,
        "freed_ambulance": freed_ambulance,
        "dispatched_from_queue": newly_dispatched,
    }
