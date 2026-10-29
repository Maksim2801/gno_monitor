from datetime import datetime

from pydantic import BaseModel


class AnomalyOut(BaseModel):
    id: int
    well_id: int
    well_name: str | None = None
    calculated_at: datetime
    algorithm: str
    anomaly_score: float
    is_anomaly: bool
    window_start: datetime | None = None
    window_end: datetime | None = None
    details: str | None = None
    features: dict | None = None

    model_config = {"from_attributes": True}


class PredictionOut(BaseModel):
    id: int
    well_id: int
    well_name: str | None = None
    calculated_at: datetime
    model_name: str
    model_version: str
    failure_probability: float
    risk_category: str
    horizon_days: int
    top_factors: list[dict] | None = None
    presumed_failure_type: str | None = None
    is_reliable: bool
    reliability_note: str | None = None
    features: dict | None = None

    model_config = {"from_attributes": True}


class AnalyticsRunResult(BaseModel):
    wells_processed: int
    anomalies_created: int
    predictions_created: int
    alerts_created: int
    skipped_insufficient_data: int
    message: str
