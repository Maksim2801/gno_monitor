from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.analytics import AnomalyResult, PredictionResult
    from app.models.fund import Well
    from app.models.user import User


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        UniqueConstraint(
            "well_id",
            "alert_type",
            "dedup_key",
            name="uq_alerts_dedup",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    well_id: Mapped[int] = mapped_column(ForeignKey("wells.id"), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="new", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    anomaly_result_id: Mapped[int | None] = mapped_column(ForeignKey("anomaly_results.id"))
    prediction_result_id: Mapped[int | None] = mapped_column(ForeignKey("prediction_results.id"))
    dedup_key: Mapped[str] = mapped_column(String(150), nullable=False)

    well: Mapped[Well] = relationship(back_populates="alerts")
    anomaly_result: Mapped[AnomalyResult | None] = relationship(back_populates="alerts")
    prediction_result: Mapped[PredictionResult | None] = relationship(back_populates="alerts")
    acknowledged_by: Mapped[User | None] = relationship()
