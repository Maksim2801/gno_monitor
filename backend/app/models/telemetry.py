from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.equipment import EquipmentUnit, Sensor
    from app.models.fund import Well


class Telemetry(Base):
    __tablename__ = "telemetry"
    __table_args__ = (
        UniqueConstraint(
            "sensor_id",
            "recorded_at",
            "idempotency_key",
            name="uq_telemetry_sensor_time_key",
        ),
        Index("ix_telemetry_well_recorded", "well_id", "recorded_at"),
        Index("ix_telemetry_sensor_recorded", "sensor_id", "recorded_at"),
        Index("ix_telemetry_param_recorded", "parameter_code", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    well_id: Mapped[int] = mapped_column(ForeignKey("wells.id"), nullable=False, index=True)
    equipment_unit_id: Mapped[int | None] = mapped_column(ForeignKey("equipment_units.id"))
    sensor_id: Mapped[int] = mapped_column(ForeignKey("sensors.id"), nullable=False, index=True)
    parameter_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    quality_flag: Mapped[str] = mapped_column(String(20), nullable=False, default="good")
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="api")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(100))

    well: Mapped[Well] = relationship(back_populates="telemetry")
    sensor: Mapped[Sensor] = relationship(back_populates="telemetry")
    equipment_unit: Mapped[EquipmentUnit | None] = relationship()
