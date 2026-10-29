from datetime import datetime

from pydantic import BaseModel

from app.schemas.alerts import AlertOut
from app.schemas.events import OperationalEventOut
from app.schemas.wells import WellListItem


class RiskDistribution(BaseModel):
    low: int = 0
    medium: int = 0
    high: int = 0
    unknown: int = 0


class DashboardOut(BaseModel):
    total_wells: int
    normal_count: int
    warning_count: int
    critical_count: int
    stopped_count: int
    active_alerts: int
    risk_distribution: RiskDistribution
    attention_wells: list[WellListItem]
    recent_events: list[OperationalEventOut]
    recent_alerts: list[AlertOut]
    generated_at: datetime
