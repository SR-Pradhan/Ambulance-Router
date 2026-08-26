from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.models import Hospital
from app.dsa.geo import haversine_km
from app.dsa.heap_ranking import rank_hospitals
from app.schemas.hospitals import NearbyHospitalsQuery, BedUpdate
from app.facilities import facility_list, hospital_has_facility
from app.api.deps import require_admin

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
            "facilities": facility_list(h),
            "distance": round(haversine_km(lat, lng, h.latitude, h.longitude), 3),
        })

    ranked = rank_hospitals(candidates, top_k=top_k)

    return {
        "patient": {"lat": lat, "lng": lng},
        "count": len(ranked),
        "hospitals": ranked,
    }


@router.get("/hospitals")
def list_hospitals(db: Session = Depends(get_db)):
    """Every hospital with its current capacity. Feeds the admin dashboard.

    ORDER BY id is not optional here. Without it Postgres returns rows in
    physical order, and UPDATE rewrites a row at the end of the table -- so
    every bed adjustment made that hospital jump to a different position in the
    dashboard table, with rows shuffling under the user's cursor as they click.
    """
    hospitals = db.query(Hospital).order_by(Hospital.id).all()
    return {
        "count": len(hospitals),
        "hospitals": [
            {
                "id": h.id,
                "name": h.name,
                "latitude": h.latitude,
                "longitude": h.longitude,
                "total_beds": h.total_beds,
                "available_beds": h.available_beds,
                "facilities": facility_list(h),
                "occupied_beds": h.total_beds - h.available_beds,
                "occupancy_percent": round(
                    (h.total_beds - h.available_beds) / h.total_beds * 100, 1
                ) if h.total_beds else 0.0,
                "accepting": h.available_beds > 0,
            }
            for h in hospitals
        ],
    }


@router.patch("/hospitals/{hospital_id}/beds")
def update_beds(
    hospital_id: int,
    payload: BedUpdate,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    """Hospital capacity management -- the second half of the problem statement.

    Setting available_beds to 0 immediately removes the hospital from dispatch,
    because rank_hospitals filters on it. That is the whole point: a hospital
    can take itself out of service without anyone touching the routing code.
    """
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if hospital is None:
        raise HTTPException(status_code=404,
                            detail=f"Hospital {hospital_id} not found")

    if payload.available_beds > hospital.total_beds:
        raise HTTPException(
            status_code=400,
            detail=(f"available_beds ({payload.available_beds}) cannot exceed "
                    f"total_beds ({hospital.total_beds}) for {hospital.name}"),
        )

    previous = hospital.available_beds
    hospital.available_beds = payload.available_beds
    db.commit()
    db.refresh(hospital)

    return {
        "id": hospital.id,
        "name": hospital.name,
        "previous_available_beds": previous,
        "available_beds": hospital.available_beds,
        "total_beds": hospital.total_beds,
        "accepting": hospital.available_beds > 0,
    }
