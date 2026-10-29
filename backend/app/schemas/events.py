from datetime import datetime

from pydantic import BaseModel, Field


class FailureCreate(BaseModel):
    well_id: int
    equipment_unit_id: int | None = None
    failure_type: str = Field(min_length=1, max_length=100)
    severity: str = "medium"
    occurred_at: datetime
    downtime_hours: float | None = None
    presumed_cause: str | None = None
    description: str | None = None


class FailureOut(BaseModel):
    id: int
    well_id: int
    well_name: str | None = None
    equipment_unit_id: int | None = None
    failure_type: str
    severity: str
    occurred_at: datetime
    downtime_hours: float | None = None
    presumed_cause: str | None = None
    description: str | None = None

    model_config = {"from_attributes": True}


class MaintenanceCreate(BaseModel):
    well_id: int
    equipment_unit_id: int | None = None
    action_type: str = Field(min_length=1, max_length=100)
    started_at: datetime
    ended_at: datetime | None = None
    performer: str | None = None
    result: str | None = None
    description: str | None = None


class MaintenanceOut(BaseModel):
    id: int
    well_id: int
    well_name: str | None = None
    equipment_unit_id: int | None = None
    action_type: str
    started_at: datetime
    ended_at: datetime | None = None
    performer: str | None = None
    result: str | None = None
    description: str | None = None

    model_config = {"from_attributes": True}


class OperationalEventOut(BaseModel):
    id: int
    event_kind: str
    well_id: int
    well_name: str | None = None
    title: str
    occurred_at: datetime
    severity: str | None = None
    description: str | None = None
