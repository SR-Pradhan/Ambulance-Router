from pydantic import BaseModel, Field


class EmergencyRequestCreate(BaseModel):
    """What a client must send to create an emergency request.

    FastAPI validates the incoming JSON against this BEFORE the endpoint runs,
    so bad input never reaches the routing logic. The ge/le bounds are real
    validation, not decoration: a latitude of 999 is rejected with a 422 and
    an error message naming the offending field.
    """

    patient_lat: float = Field(..., ge=-90, le=90,
                               description="Patient latitude, -90 to 90")
    patient_lng: float = Field(..., ge=-180, le=180,
                               description="Patient longitude, -180 to 180")

    model_config = {
        "json_schema_extra": {
            "example": {"patient_lat": 28.44, "patient_lng": 77.00}
        }
    }
