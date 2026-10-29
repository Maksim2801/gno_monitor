from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_write
from app.db.session import get_db
from app.models import AnomalyResult, PredictionResult, Sensor, Telemetry, User
from app.schemas.common import PaginatedResponse
from app.schemas.wells import (
    AnomalyBrief,
    EquipmentOut,
    OilFieldOut,
    PredictionBrief,
    SensorOut,
    WellCreate,
    WellDetail,
    WellListItem,
    WellPadOut,
    WellUpdate,
)
from app.services.well_service import WellService

router = APIRouter()


@router.get("", response_model=PaginatedResponse[WellListItem])
def list_wells(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    search: str | None = None,
    status: str | None = None,
    oil_field_id: int | None = None,
    risk_category: str | None = None,
    sort_by: str = "name",
    sort_dir: str = "asc",
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return WellService(db).list_wells(
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        oil_field_id=oil_field_id,
        risk_category=risk_category,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("/meta/fields", response_model=list[OilFieldOut])
def list_fields(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return WellService(db).list_fields()


@router.get("/meta/pads", response_model=list[WellPadOut])
def list_pads(
    oil_field_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    pads = WellService(db).list_pads(oil_field_id)
    return [
        {
            "id": p.id,
            "name": p.name,
            "code": p.code,
            "oil_field_id": p.oil_field_id,
            "oil_field_name": p.oil_field.name if p.oil_field else None,
        }
        for p in pads
    ]


@router.get("/{well_id}", response_model=WellDetail)
def get_well(
    well_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    well = WellService(db).get_well(well_id)
    if not well:
        raise HTTPException(status_code=404, detail="Скважина не найдена")

    sensors = (
        db.query(Sensor)
        .options(joinedload(Sensor.sensor_type))
        .filter(Sensor.well_id == well_id)
        .all()
    )
    latest_pred = (
        db.query(PredictionResult)
        .filter(PredictionResult.well_id == well_id)
        .order_by(PredictionResult.calculated_at.desc())
        .first()
    )
    latest_anom = (
        db.query(AnomalyResult)
        .filter(AnomalyResult.well_id == well_id)
        .order_by(AnomalyResult.calculated_at.desc())
        .first()
    )

    since = datetime.now(timezone.utc) - timedelta(hours=6)
    latest_rows = (
        db.query(Telemetry)
        .filter(Telemetry.well_id == well_id, Telemetry.recorded_at >= since)
        .order_by(Telemetry.recorded_at.desc())
        .limit(500)
        .all()
    )
    latest_telemetry: dict[str, float | None] = {}
    for row in latest_rows:
        if row.parameter_code not in latest_telemetry:
            latest_telemetry[row.parameter_code] = row.value

    from app.models import Alert
    from sqlalchemy import func

    active_alerts = (
        db.query(func.count(Alert.id))
        .filter(Alert.well_id == well_id, Alert.status == "new")
        .scalar()
        or 0
    )

    return WellDetail(
        id=well.id,
        name=well.name,
        inventory_number=well.inventory_number,
        status=well.status,
        depth_m=well.depth_m,
        notes=well.notes,
        commissioning_date=well.commissioning_date,
        oil_field=OilFieldOut.model_validate(well.well_pad.oil_field),
        well_pad=WellPadOut(
            id=well.well_pad.id,
            name=well.well_pad.name,
            code=well.well_pad.code,
            oil_field_id=well.well_pad.oil_field_id,
            oil_field_name=well.well_pad.oil_field.name,
        ),
        equipment=[EquipmentOut.model_validate(e) for e in well.equipment_units],
        sensors=[
            SensorOut(
                id=s.id,
                tag=s.tag,
                parameter_code=s.sensor_type.code,
                parameter_name=s.sensor_type.name,
                unit=s.sensor_type.unit,
                is_active=s.is_active,
            )
            for s in sensors
        ],
        latest_prediction=PredictionBrief.model_validate(latest_pred) if latest_pred else None,
        latest_anomaly=AnomalyBrief.model_validate(latest_anom) if latest_anom else None,
        latest_telemetry=latest_telemetry,
        active_alerts=active_alerts,
    )


@router.post("", response_model=WellListItem, status_code=201)
def create_well(
    payload: WellCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_write),
):
    try:
        well = WellService(db).create_well(payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    items = WellService(db).list_wells(page=1, page_size=1, search=well.name)["items"]
    return items[0]


@router.patch("/{well_id}", response_model=WellDetail)
def update_well(
    well_id: int,
    payload: WellUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_write),
):
    try:
        WellService(db).update_well(well_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return get_well(well_id, db, user)
