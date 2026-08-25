from typing import Literal, Optional

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
    # Literal gives a closed set: anything else is rejected with a 422 naming
    # the allowed values, so an invalid severity can never reach the queue.
    severity: Literal["critical", "urgent", "standard"] = Field(
        "standard", description="Triage severity; drives dispatch order")
    # A missing facility is a HARD constraint, not a preference: a hospital
    # without a cardiac unit cannot treat a cardiac case at any distance.
    required_facility: Optional[Literal["icu", "trauma", "cardiac"]] = Field(
        None, description="Specialist unit the patient needs, if any")

    model_config = {
        "json_schema_extra": {
            "example": {"patient_lat": 28.44, "patient_lng": 77.00,
                        "severity": "critical", "required_facility": "cardiac"}
        }
    }
