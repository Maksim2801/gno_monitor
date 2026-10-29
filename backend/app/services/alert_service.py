from datetime import datetime, timezone
from math import ceil

from sqlalchemy.orm import Session, joinedload

from app.core.constants import ALERT_STATUS_ACKNOWLEDGED, ALERT_STATUS_CLOSED, ALERT_STATUS_NEW
from app.models import Alert


class AlertService:
    def __init__(self, db: Session):
        self.db = db

    def list_alerts(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        well_id: int | None = None,
        severity: str | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        q = self.db.query(Alert).options(joinedload(Alert.well))
        if well_id:
            q = q.filter(Alert.well_id == well_id)
        if severity:
            q = q.filter(Alert.severity == severity)
        if status:
            q = q.filter(Alert.status == status)
        if date_from:
            q = q.filter(Alert.created_at >= date_from)
        if date_to:
            q = q.filter(Alert.created_at <= date_to)
        total = q.count()
        rows = (
            q.order_by(Alert.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        items = [
            {
                "id": r.id,
                "well_id": r.well_id,
                "well_name": r.well.name if r.well else None,
                "alert_type": r.alert_type,
                "severity": r.severity,
                "message": r.message,
                "status": r.status,
                "created_at": r.created_at,
                "acknowledged_at": r.acknowledged_at,
                "closed_at": r.closed_at,
                "anomaly_result_id": r.anomaly_result_id,
                "prediction_result_id": r.prediction_result_id,
            }
            for r in rows
        ]
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": max(ceil(total / page_size), 1) if total else 0,
        }

    def get(self, alert_id: int) -> Alert | None:
        return (
            self.db.query(Alert)
            .options(joinedload(Alert.well))
            .filter(Alert.id == alert_id)
            .first()
        )

    def update_status(self, alert_id: int, status: str, user_id: int) -> Alert:
        alert = self.get(alert_id)
        if not alert:
            raise LookupError("Уведомление не найдено")
        now = datetime.now(timezone.utc)
        if status == ALERT_STATUS_ACKNOWLEDGED:
            alert.status = ALERT_STATUS_ACKNOWLEDGED
            alert.acknowledged_at = now
            alert.acknowledged_by_id = user_id
        elif status == ALERT_STATUS_CLOSED:
            alert.status = ALERT_STATUS_CLOSED
            alert.closed_at = now
            if not alert.acknowledged_at:
                alert.acknowledged_at = now
                alert.acknowledged_by_id = user_id
        elif status == ALERT_STATUS_NEW:
            alert.status = ALERT_STATUS_NEW
            alert.acknowledged_at = None
            alert.closed_at = None
            alert.acknowledged_by_id = None
        else:
            raise ValueError("Недопустимый статус")
        self.db.commit()
        self.db.refresh(alert)
        return alert
