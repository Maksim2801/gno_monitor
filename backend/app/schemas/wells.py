from datetime import datetime

from pydantic import BaseModel, Field


class OilFieldOut(BaseModel):
    id: int
    name: str
    code: str
    region: str | None = None

    model_config = {"from_attributes": True}


class WellPadOut(BaseModel):
    id: int
    name: str
    code: str
    oil_field_id: int
    oil_field_name: str | None = None

    model_config = {"from_attributes": True}


class EquipmentOut(BaseModel):
    id: int
    equipment_type: str
    name: str
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    rated_power_kw: float | None = None
    rated_current_a: float | None = None
    rated_voltage_v: float | None = None
    status: str

    model_config = {"from_attributes": True}


class SensorOut(BaseModel):
    id: int
    tag: str
    parameter_code: str
    parameter_name: str
    unit: str
    is_active: bool

    model_config = {"from_attributes": True}


class WellListItem(BaseModel):
    id: int
    name: str
    inventory_number: str | None = None
    status: str
    depth_m: float | None = None
    oil_field: str
    well_pad: str
    risk_category: str | None = None
    failure_probability: float | None = None
    active_alerts: int = 0

    model_config = {"from_attributes": True}


class WellCreate(BaseModel):
    well_pad_id: int
    name: str = Field(min_length=1, max_length=100)
    inventory_number: str | None = None
    depth_m: float | None = None
    status: str = "normal"
    notes: str | None = None


class WellUpdate(BaseModel):
    inventory_number: str | None = None
    depth_m: float | None = None
    status: str | None = None
    notes: str | None = None
    well_pad_id: int | None = None


class PredictionBrief(BaseModel):
    id: int
    failure_probability: float
    risk_category: str
    horizon_days: int
    calculated_at: datetime
    top_factors: list[dict] | None = None
    is_reliable: bool
    reliability_note: str | None = None
    model_name: str

    model_config = {"from_attributes": True}


class AnomalyBrief(BaseModel):
    id: int
    anomaly_score: float
    is_anomaly: bool
    algorithm: str
    calculated_at: datetime
    details: str | None = None

    model_config = {"from_attributes": True}


class WellDetail(BaseModel):
    id: int
    name: str
    inventory_number: str | None = None
    status: str
    depth_m: float | None = None
    notes: str | None = None
    commissioning_date: datetime | None = None
    oil_field: OilFieldOut
    well_pad: WellPadOut
    equipment: list[EquipmentOut]
    sensors: list[SensorOut]
    latest_prediction: PredictionBrief | None = None
    latest_anomaly: AnomalyBrief | None = None
    latest_telemetry: dict[str, float | None] = {}
    active_alerts: int = 0
