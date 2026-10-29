from datetime import datetime

from pydantic import BaseModel, Field


class TelemetryPointIn(BaseModel):
    sensor_tag: str | None = None
    sensor_id: int | None = None
    parameter_code: str | None = None
    value: float
    recorded_at: datetime
    quality_flag: str = "good"
    source: str = "api"
    idempotency_key: str | None = Field(default=None, max_length=100)


class TelemetryBatchIn(BaseModel):
    well_id: int
    points: list[TelemetryPointIn] = Field(min_length=1, max_length=5000)
    batch_id: str | None = Field(default=None, max_length=100)


class TelemetryPointOut(BaseModel):
    id: int
    well_id: int
    sensor_id: int
    parameter_code: str
    value: float
    unit: str
    quality_flag: str
    source: str
    recorded_at: datetime

    model_config = {"from_attributes": True}


class TelemetrySeriesOut(BaseModel):
    parameter_code: str
    unit: str
    points: list[TelemetryPointOut]


class TelemetryIngestResult(BaseModel):
    accepted: int
    skipped_duplicates: int
    rejected: int
    errors: list[str] = []
