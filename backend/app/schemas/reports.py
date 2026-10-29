from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    report_type: str = Field(
        pattern="^(fund_summary|well|telemetry|failures|analytics|alerts)$"
    )
    period_start: datetime
    period_end: datetime
    well_id: int | None = None
    oil_field_id: int | None = None
    export_format: str | None = Field(default="json", pattern="^(json|csv|pdf)$")


class ReportOut(BaseModel):
    id: int
    report_type: str
    title: str
    period_start: datetime
    period_end: datetime
    parameters: dict[str, Any] | None = None
    content_json: dict[str, Any] | None = None
    content_text: str | None = None
    file_format: str | None = None
    created_by_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
