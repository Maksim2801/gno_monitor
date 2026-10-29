from datetime import datetime

from pydantic import BaseModel, Field


class AlertOut(BaseModel):
    id: int
    well_id: int
    well_name: str | None = None
    alert_type: str
    severity: str
    message: str
    status: str
    created_at: datetime
    acknowledged_at: datetime | None = None
    closed_at: datetime | None = None
    anomaly_result_id: int | None = None
    prediction_result_id: int | None = None

    model_config = {"from_attributes": True}


class AlertStatusUpdate(BaseModel):
    status: str = Field(pattern="^(acknowledged|closed|new)$")
