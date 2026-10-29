from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.alerts import Alert
    from app.models.analytics import AnomalyResult, PredictionResult
    from app.models.equipment import EquipmentUnit, Sensor
    from app.models.events import Failure, MaintenanceAction, OperationalState
    from app.models.telemetry import Telemetry


class OilField(Base):
    __tablename__ = "oil_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    region: Mapped[str | None] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text)

    well_pads: Mapped[list[WellPad]] = relationship(back_populates="oil_field")


class WellPad(Base):
    __tablename__ = "well_pads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    oil_field_id: Mapped[int] = mapped_column(ForeignKey("oil_fields.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    oil_field: Mapped[OilField] = relationship(back_populates="well_pads")
    wells: Mapped[list[Well]] = relationship(back_populates="well_pad")


class Well(Base):
    __tablename__ = "wells"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    well_pad_id: Mapped[int] = mapped_column(ForeignKey("well_pads.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    inventory_number: Mapped[str | None] = mapped_column(String(100))
    depth_m: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="normal", index=True)
    commissioning_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    well_pad: Mapped[WellPad] = relationship(back_populates="wells")
    equipment_units: Mapped[list[EquipmentUnit]] = relationship(back_populates="well")
    sensors: Mapped[list[Sensor]] = relationship(back_populates="well")
    telemetry: Mapped[list[Telemetry]] = relationship(back_populates="well")
    operational_states: Mapped[list[OperationalState]] = relationship(back_populates="well")
    failures: Mapped[list[Failure]] = relationship(back_populates="well")
    maintenance_actions: Mapped[list[MaintenanceAction]] = relationship(back_populates="well")
    anomaly_results: Mapped[list[AnomalyResult]] = relationship(back_populates="well")
    prediction_results: Mapped[list[PredictionResult]] = relationship(back_populates="well")
    alerts: Mapped[list[Alert]] = relationship(back_populates="well")
