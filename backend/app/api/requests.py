from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.models import Hospital, Ambulance, EmergencyRequest
from app.graph_loader import load_road_network, path_length_km
from app.schemas.requests import EmergencyRequestCreate
from app.dsa.dijkstra import dijkstra_all, reconstruct_path
from app.dsa.geo import snap_to_node
from app.dsa.heap_ranking import (rank_hospitals, rank_by_distance,
                                  CAPACITY_PENALTY_MINUTES)
from app.dsa.priority_queue import PriorityQueue, triage_score
from app.facilities import facility_list, hospital_has_facility, FACILITY_LABELS
from app.api.deps import require_admin

router = APIRouter()

# Assumed average ambulance speed. This is a SIMPLIFICATION: there is no live
# traffic data in this project, so ETA is just distance / speed. A real system
# would use time-of-day traffic, road types and priority-vehicle rules.
AVG_AMBULANCE_SPEED_KMH = 40.0


def compute_best_route(db: Session, patient_lat: float, patient_lng: float,
                       required_facility: str | None = None):
    """Pick the best hospital for a patient and route to it.

    This is where the two halves of the project finally meet: the heap picks
    the hospital, Dijkstra finds the road route. Ranking is on ROAD distance,
    not straight-line -- which is the whole point of this version.

    Returns a result dict, or None if no hospital with free beds is reachable.
    """
    # 1. Load the road network (shared loader - see app/graph_loader.py).
    graph, coords = load_road_network(db)

    if not coords:
        return {"error": "no_road_network"}

    # 2. The patient gave us a coordinate; Dijkstra needs a node.
    patient_node, patient_offset = snap_to_node(patient_lat, patient_lng, coords)

    # 3. ONE Dijkstra run gives the travel TIME to every node, and therefore to
    #    every hospital. Since v1.7 the graph is weighted in minutes, so these
    #    are durations, not distances. Running it once per hospital would
    #    repeat this work.
    distances, prev = dijkstra_all(graph, patient_node)

    # 4. Build the candidate list, measured by road distance.
    candidates = []
    rejected_for_facility = 0
    for h in db.query(Hospital).all():
        if h.available_beds <= 0:
            continue  # full - the heap would drop it anyway, but skip the work

        # A missing specialist unit is a hard constraint, exactly like zero
        # beds. It is filtered here rather than penalised in the score: no
        # amount of free beds makes a hospital able to treat a cardiac case.
        if not hospital_has_facility(h, required_facility):
            rejected_for_facility += 1
            continue

        h_node, h_offset = snap_to_node(h.latitude, h.longitude, coords)
        minutes = distances.get(h_node, float('inf'))
        if minutes == float('inf'):
            continue  # unreachable from the patient (e.g. disconnected road)

        # Ranking happens on TIME; the kilometres are carried alongside purely
        # so the answer can be explained to a human.
        h_path = reconstruct_path(prev, patient_node, h_node)
        road_km = path_length_km(h_path, coords)

        candidates.append({
            "id": h.id,
            "name": h.name,
            "latitude": h.latitude,
            "longitude": h.longitude,
            "available_beds": h.available_beds,
            "total_beds": h.total_beds,
            "facilities": facility_list(h),
            "node_id": h_node,
            "distance": round(road_km, 3),          # physical km, for display
            "travel_minutes": round(minutes, 2),    # the key the heap ranks on
            "distance_type": "road",
        })

    if not candidates:
        # Distinguish "everywhere is full" from "nowhere has the right unit",
        # because they call for completely different responses in real life.
        return {
            "error": "no_candidate",
            "required_facility": required_facility,
            "rejected_for_facility": rejected_for_facility,
        }

    # 5. The heap picks the winner. rank_hospitals doesn't know or care that
    #    "distance" is now road distance rather than straight-line.
    ranked = rank_hospitals(candidates, top_k=len(candidates),
                            capacity_penalty_km=CAPACITY_PENALTY_MINUTES,
                            cost_key="travel_minutes")
    best = ranked[0]

    # 6. The actual route to the winner, and how long it should take.
    path = reconstruct_path(prev, patient_node, best["node_id"])
    # The ETA is the routed travel time itself. Before v1.7 it was derived from
    # distance and a flat assumed speed; now traffic is already baked into the
    # edge weights, so the number the router produced IS the estimate.
    eta_minutes = round(best["travel_minutes"], 1)

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
        pickup_minutes = distances.get(a_node, float('inf'))
        if pickup_minutes == float('inf'):
            continue
        a_path = reconstruct_path(prev, patient_node, a_node)
        ambulance_candidates.append({
            "id": a.id,
            "current_lat": a.current_lat,
            "current_lng": a.current_lng,
            "node_id": a_node,
            "distance": round(path_length_km(a_path, coords), 3),
            "travel_minutes": round(pickup_minutes, 2),
        })

    # Nearest by TIME, not by distance: a closer ambulance stuck behind traffic
    # is not the one that arrives first.
    nearest = rank_by_distance(ambulance_candidates, top_k=1,
                               key="travel_minutes")
    ambulance = nearest[0] if nearest else None

    if ambulance is not None:
        ambulance["pickup_path"] = reconstruct_path(
            prev, patient_node, ambulance["node_id"]
        )
        ambulance["pickup_eta_minutes"] = round(ambulance["travel_minutes"], 1)

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
            "traffic_aware": True,
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
        result = compute_best_route(db, req.patient_lat, req.patient_lng,
                                    req.required_facility)
        if _failed(result) or result["ambulance"] is None:
            continue  # no eligible hospital, or no usable ambulance

        vehicle = db.query(Ambulance).filter(
            Ambulance.id == result["ambulance"]["id"]
        ).first()
        if vehicle is None or vehicle.status != "available":
            continue

        req.assigned_hospital_id = result["hospital"]["id"]
        req.assigned_ambulance_id = vehicle.id
        req.status = "en_route"
        # The journey clock starts HERE, not at req.created_at.
        req.dispatched_at = datetime.now()
        vehicle.status = "busy"
        dispatched.append(req)

    if dispatched:
        db.commit()
    return dispatched


def _failed(result):
    """compute_best_route returns a dict either way; this is the failure check."""
    return result is None or "error" in result


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
    result = compute_best_route(db, payload.patient_lat, payload.patient_lng,
                                payload.required_facility)

    if _failed(result):
        # Say WHICH constraint could not be met. "No hospital has a cardiac
        # unit free" and "everywhere is full" need different responses.
        if result.get("rejected_for_facility"):
            unit = FACILITY_LABELS.get(payload.required_facility,
                                       payload.required_facility)
            detail = (f"No reachable hospital with free beds has a {unit}. "
                      f"{result['rejected_for_facility']} hospital(s) had beds "
                      f"but lacked the required unit.")
        else:
            detail = "No hospital with available beds is reachable from this location."
        raise HTTPException(status_code=503, detail=detail)

    # The request is created as PENDING and joins the triage queue. It does not
    # grab an ambulance directly -- dispatch_waiting decides who gets the next
    # free vehicle, so a critical patient already waiting is served before a
    # standard one that just arrived.
    emergency = EmergencyRequest(
        patient_lat=payload.patient_lat,
        patient_lng=payload.patient_lng,
        severity=payload.severity,
        required_facility=payload.required_facility,
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
    same_as_proposed = False
    if emergency.assigned_ambulance_id is not None:
        proposed = result.get("ambulance")
        # The queue may have handed the proposed ambulance to a more urgent
        # patient. Only reuse the computed pickup leg when the ambulance that
        # was actually assigned is the one the route was computed for.
        same_as_proposed = bool(
            proposed and proposed["id"] == emergency.assigned_ambulance_id
        )
        if same_as_proposed:
            assigned = proposed
        else:
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
        "required_facility": emergency.required_facility,
        "created_at": emergency.created_at,
        **result,
        "ambulance": assigned,
        "queued_behind": queued_ahead,
        # Only report a total ETA when it belongs to the ambulance that was
        # actually assigned; otherwise it would be a number for a different
        # vehicle's journey.
        "total_eta_minutes": (
            result["total_eta_minutes"] if same_as_proposed else None
        ),
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

    result = compute_best_route(db, emergency.patient_lat, emergency.patient_lng,
                                emergency.required_facility)

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
        "required_facility": emergency.required_facility,
        "route": None if _failed(result) else result["route"],
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
                "required_facility": r.required_facility,
                "assigned_hospital_id": r.assigned_hospital_id,
                "assigned_hospital_name": hospitals.get(r.assigned_hospital_id),
                "assigned_ambulance_id": r.assigned_ambulance_id,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }


@router.patch("/requests/{request_id}/complete")
def complete_request(
    request_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
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
