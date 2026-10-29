from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_write
from app.db.session import get_db
from app.models import User
from app.schemas.events import (
    FailureCreate,
    FailureOut,
    MaintenanceCreate,
    MaintenanceOut,
    OperationalEventOut,
)
from app.services.event_service import EventService

router = APIRouter()


@router.get("", response_model=list[OperationalEventOut])
def list_events(
    well_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return EventService(db).list_combined_events(
        well_id=well_id, date_from=date_from, date_to=date_to, limit=limit
    )


@router.get("/failures", response_model=list[FailureOut])
def list_failures(
    well_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return EventService(db).list_failures(well_id=well_id, date_from=date_from, date_to=date_to)


@router.post("/failures", response_model=FailureOut, status_code=201)
def create_failure(
    payload: FailureCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_write),
):
    try:
        row = EventService(db).create_failure(payload, user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "id": row.id,
        "well_id": row.well_id,
        "well_name": None,
        "equipment_unit_id": row.equipment_unit_id,
        "failure_type": row.failure_type,
        "severity": row.severity,
        "occurred_at": row.occurred_at,
        "downtime_hours": row.downtime_hours,
        "presumed_cause": row.presumed_cause,
        "description": row.description,
    }


@router.get("/maintenance", response_model=list[MaintenanceOut])
def list_maintenance(
    well_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return EventService(db).list_maintenance(
        well_id=well_id, date_from=date_from, date_to=date_to
    )


@router.post("/maintenance", response_model=MaintenanceOut, status_code=201)
def create_maintenance(
    payload: MaintenanceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_write),
):
    try:
        row = EventService(db).create_maintenance(payload, user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": row.id,
        "well_id": row.well_id,
        "well_name": None,
        "equipment_unit_id": row.equipment_unit_id,
        "action_type": row.action_type,
        "started_at": row.started_at,
        "ended_at": row.ended_at,
        "performer": row.performer,
        "result": row.result,
        "description": row.description,
    }
