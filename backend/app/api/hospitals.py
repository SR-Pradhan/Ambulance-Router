from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.models import Hospital
from app.dsa.geo import haversine_km
from app.dsa.heap_ranking import rank_hospitals
from app.schemas.hospitals import NearbyHospitalsQuery

router = APIRouter()


@router.get("/hospitals/nearby")
def get_nearby_hospitals(
    params: NearbyHospitalsQuery = Depends(),
    db: Session = Depends(get_db),
):
    """Rank hospitals by STRAIGHT-LINE distance from a point.

    Kept deliberately as straight-line: POST /requests ranks the same hospitals
    by real road distance, and comparing the two shows why that matters.
    """
    lat, lng, top_k = params.lat, params.lng, params.top_k
    hospitals = db.query(Hospital).all()

    candidates = []
    for h in hospitals:
        candidates.append({
            "id": h.id,
            "name": h.name,
            "latitude": h.latitude,
            "longitude": h.longitude,
            "available_beds": h.available_beds,
            "total_beds": h.total_beds,
            "distance": round(haversine_km(lat, lng, h.latitude, h.longitude), 3),
        })

    ranked = rank_hospitals(candidates, top_k=top_k)

    return {
        "patient": {"lat": lat, "lng": lng},
        "count": len(ranked),
        "hospitals": ranked,
    }
