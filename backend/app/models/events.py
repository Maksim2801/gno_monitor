from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.equipment import EquipmentUnit
    from app.models.fund import Well
    from app.models.user import User


class OperationalState(Base):
    __tablename__ = "operational_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    well_id: Mapped[int] = mapped_column(ForeignKey("wells.id"), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    description: Mapped[str | None] = mapped_column(Text)

    well: Mapped[Well] = relationship(back_populates="operational_states")


class Failure(Base):
    __tablename__ = "failures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    well_id: Mapped[int] = mapped_column(ForeignKey("wells.id"), nullable=False, index=True)
    equipment_unit_id: Mapped[int | None] = mapped_column(ForeignKey("equipment_units.id"))
    failure_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False, default="medium")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    downtime_hours: Mapped[float | None] = mapped_column(Float)
    presumed_cause: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    well: Mapped[Well] = relationship(back_populates="failures")
    equipment_unit: Mapped[EquipmentUnit | None] = relationship()
    created_by: Mapped[User | None] = relationship()


class MaintenanceAction(Base):
    __tablename__ = "maintenance_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    well_id: Mapped[int] = mapped_column(ForeignKey("wells.id"), nullable=False, index=True)
    equipment_unit_id: Mapped[int | None] = mapped_column(ForeignKey("equipment_units.id"))
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    performer: Mapped[str | None] = mapped_column(String(150))
    result: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    well: Mapped[Well] = relationship(back_populates="maintenance_actions")
    equipment_unit: Mapped[EquipmentUnit | None] = relationship()
    created_by: Mapped[User | None] = relationship()
