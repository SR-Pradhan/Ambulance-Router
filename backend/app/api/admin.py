from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.models import Hospital, Ambulance, EmergencyRequest

router = APIRouter()


@router.get("/admin/overview")
def admin_overview(db: Session = Depends(get_db)):
    """One aggregate snapshot for the dashboard.

    Deliberately a single endpoint rather than four: a dashboard that fires four
    separate requests can render a self-contradictory picture, because each
    reply is a snapshot from a slightly different moment. One query set, read
    inside one session, is consistent with itself.
    """
    hospitals = db.query(Hospital).all()
    ambulances = db.query(Ambulance).all()
    requests = db.query(EmergencyRequest).all()

    total_beds = sum(h.total_beds for h in hospitals)
    available_beds = sum(h.available_beds for h in hospitals)

    return {
        "hospitals": {
            "count": len(hospitals),
            "total_beds": total_beds,
            "available_beds": available_beds,
            "occupied_beds": total_beds - available_beds,
            "occupancy_percent": round(
                (total_beds - available_beds) / total_beds * 100, 1
            ) if total_beds else 0.0,
            # A hospital at 0 free beds is invisible to dispatch, so this is the
            # number that actually matters operationally.
            "accepting_patients": sum(1 for h in hospitals if h.available_beds > 0),
            "full": sum(1 for h in hospitals if h.available_beds <= 0),
        },
        "ambulances": {
            "count": len(ambulances),
            "available": sum(1 for a in ambulances if a.status == "available"),
            "busy": sum(1 for a in ambulances if a.status == "busy"),
        },
        "requests": {
            "count": len(requests),
            "pending": sum(1 for r in requests if r.status == "pending"),
            "en_route": sum(1 for r in requests if r.status == "en_route"),
            "completed": sum(1 for r in requests if r.status == "completed"),
            # Requests that found a hospital but no ambulance: the queue that a
            # dispatcher would need to watch.
            "awaiting_ambulance": sum(
                1 for r in requests
                if r.status == "pending" and r.assigned_ambulance_id is None
            ),
        },
        "note": "All data is simulated. Not a medically validated system.",
    }
