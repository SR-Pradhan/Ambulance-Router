from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.models import RoadNode, RoadEdge, Hospital, Ambulance, EmergencyRequest
from app.schemas.requests import EmergencyRequestCreate
from app.dsa.graph import Graph
from app.dsa.dijkstra import dijkstra_all, reconstruct_path
from app.dsa.geo import snap_to_node
from app.dsa.heap_ranking import rank_hospitals, rank_by_distance

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
    # 1. Load the road network.
    coords = {n.id: (n.lat, n.lng) for n in db.query(RoadNode).all()}
    graph = Graph()
    for e in db.query(RoadEdge).all():
        graph.add_edge(e.from_node_id, e.to_node_id, e.weight)

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


@router.post("/requests")
def create_request(payload: EmergencyRequestCreate, db: Session = Depends(get_db)):
    """Create an emergency request: choose a hospital, route to it, store it."""
    result = compute_best_route(db, payload.patient_lat, payload.patient_lng)

    if result is None:
        raise HTTPException(
            status_code=503,
            detail="No hospital with available beds is reachable from this location.",
        )

    # Dispatch the nearest available ambulance, if there is one. A request with
    # no ambulance is still worth creating -- the hospital choice stands and the
    # request simply waits, which is why this is not an error.
    ambulance = result["ambulance"]

    emergency = EmergencyRequest(
        patient_lat=payload.patient_lat,
        patient_lng=payload.patient_lng,
        assigned_hospital_id=result["hospital"]["id"],
        assigned_ambulance_id=ambulance["id"] if ambulance else None,
        # "en_route" once an ambulance is actually on its way; otherwise it
        # stays "pending" until one frees up.
        status="en_route" if ambulance else "pending",
    )
    db.add(emergency)

    if ambulance:
        # Take the ambulance out of the available pool so the next request
        # cannot be given the same one.
        vehicle = db.query(Ambulance).filter(Ambulance.id == ambulance["id"]).first()
        if vehicle:
            vehicle.status = "busy"

    db.commit()
    db.refresh(emergency)

    return {
        "request_id": emergency.id,
        "status": emergency.status,
        "created_at": emergency.created_at,
        **result,
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
