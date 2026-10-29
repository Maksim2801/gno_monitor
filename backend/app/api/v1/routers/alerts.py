from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_alert_action
from app.db.session import get_db
from app.models import User
from app.schemas.alerts import AlertOut, AlertStatusUpdate
from app.schemas.common import PaginatedResponse
from app.services.alert_service import AlertService

router = APIRouter()


@router.get("", response_model=PaginatedResponse[AlertOut])
def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    well_id: int | None = None,
    severity: str | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return AlertService(db).list_alerts(
        page=page,
        page_size=page_size,
        well_id=well_id,
        severity=severity,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/{alert_id}", response_model=AlertOut)
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    alert = AlertService(db).get(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Уведомление не найдено")
    return {
        "id": alert.id,
        "well_id": alert.well_id,
        "well_name": alert.well.name if alert.well else None,
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "message": alert.message,
        "status": alert.status,
        "created_at": alert.created_at,
        "acknowledged_at": alert.acknowledged_at,
        "closed_at": alert.closed_at,
        "anomaly_result_id": alert.anomaly_result_id,
        "prediction_result_id": alert.prediction_result_id,
    }


@router.patch("/{alert_id}", response_model=AlertOut)
def update_alert(
    alert_id: int,
    payload: AlertStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_alert_action),
):
    try:
        alert = AlertService(db).update_status(alert_id, payload.status, user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return get_alert(alert_id, db, user)
