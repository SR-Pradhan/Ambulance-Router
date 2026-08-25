from pydantic import BaseModel, Field


class NearbyHospitalsQuery(BaseModel):
    """Validated query parameters for GET /hospitals/nearby.

    Used with Depends(), which tells FastAPI to build this model from the query
    string and validate it before the endpoint runs. Previously these were bare
    function arguments with no bounds at all, so `top_k=-1` was accepted and
    silently returned an empty list -- a wrong answer rather than an error.
    """

    lat: float = Field(..., ge=-90, le=90,
                       description="Patient latitude, -90 to 90")
    lng: float = Field(..., ge=-180, le=180,
                       description="Patient longitude, -180 to 180")
    top_k: int = Field(3, ge=1, le=50,
                       description="How many hospitals to return (1-50)")


class BedUpdate(BaseModel):
    """Body for PATCH /hospitals/{id}/beds.

    Only a lower bound is enforced here. The upper bound (beds must not exceed
    the hospital's total) is a CROSS-FIELD rule that depends on a database row,
    which Pydantic cannot see -- so it is checked in the endpoint and returned
    as a 400.
    """

    available_beds: int = Field(..., ge=0,
                                description="Free beds; cannot exceed total_beds")
