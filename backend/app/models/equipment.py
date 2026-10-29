from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.fund import Well
    from app.models.telemetry import Telemetry


class EquipmentUnit(Base):
    __tablename__ = "equipment_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    well_id: Mapped[int] = mapped_column(ForeignKey("wells.id"), nullable=False, index=True)
    equipment_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(150))
    model: Mapped[str | None] = mapped_column(String(150))
    serial_number: Mapped[str | None] = mapped_column(String(100))
    rated_power_kw: Mapped[float | None] = mapped_column(Float)
    rated_current_a: Mapped[float | None] = mapped_column(Float)
    rated_voltage_v: Mapped[float | None] = mapped_column(Float)
    install_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="operating")
    notes: Mapped[str | None] = mapped_column(Text)

    well: Mapped[Well] = relationship(back_populates="equipment_units")
    sensors: Mapped[list[Sensor]] = relationship(back_populates="equipment_unit")


class SensorType(Base):
    __tablename__ = "sensor_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    min_value: Mapped[float | None] = mapped_column(Float)
    max_value: Mapped[float | None] = mapped_column(Float)
    critical_min: Mapped[float | None] = mapped_column(Float)
    critical_max: Mapped[float | None] = mapped_column(Float)

    sensors: Mapped[list[Sensor]] = relationship(back_populates="sensor_type")


class Sensor(Base):
    __tablename__ = "sensors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    well_id: Mapped[int] = mapped_column(ForeignKey("wells.id"), nullable=False, index=True)
    equipment_unit_id: Mapped[int | None] = mapped_column(ForeignKey("equipment_units.id"))
    sensor_type_id: Mapped[int] = mapped_column(ForeignKey("sensor_types.id"), nullable=False)
    tag: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    well: Mapped[Well] = relationship(back_populates="sensors")
    equipment_unit: Mapped[EquipmentUnit | None] = relationship(back_populates="sensors")
    sensor_type: Mapped[SensorType] = relationship(back_populates="sensors")
    telemetry: Mapped[list[Telemetry]] = relationship(back_populates="sensor")
