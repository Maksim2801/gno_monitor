from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.analytics.pipeline import AnalyticsPipeline
from app.api.deps import get_current_user, require_write
from app.db.session import get_db
from app.models import AnomalyResult, PredictionResult, User
from app.schemas.analytics import AnalyticsRunResult, AnomalyOut, PredictionOut

router = APIRouter()


@router.post("/run", response_model=AnalyticsRunResult)
def run_analytics(
    well_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_write),
):
    well_ids = [well_id] if well_id else None
    stats = AnalyticsPipeline(db).run(well_ids=well_ids)
    return AnalyticsRunResult(
        wells_processed=int(stats["wells_processed"]),
        anomalies_created=int(stats["anomalies_created"]),
        predictions_created=int(stats["predictions_created"]),
        alerts_created=int(stats["alerts_created"]),
        skipped_insufficient_data=int(stats["skipped_insufficient_data"]),
        message=str(stats["message"]),
    )


@router.get("/predictions", response_model=list[PredictionOut])
def list_predictions(
    well_id: int | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(PredictionResult).options(joinedload(PredictionResult.well))
    if well_id:
        q = q.filter(PredictionResult.well_id == well_id)
    rows = q.order_by(PredictionResult.calculated_at.desc()).limit(limit).all()
    return [
        PredictionOut(
            id=r.id,
            well_id=r.well_id,
            well_name=r.well.name if r.well else None,
            calculated_at=r.calculated_at,
            model_name=r.model_name,
            model_version=r.model_version,
            failure_probability=r.failure_probability,
            risk_category=r.risk_category,
            horizon_days=r.horizon_days,
            top_factors=r.top_factors,
            presumed_failure_type=r.presumed_failure_type,
            is_reliable=r.is_reliable,
            reliability_note=r.reliability_note,
            features=r.features,
        )
        for r in rows
    ]


@router.get("/wells/{well_id}/predictions", response_model=list[PredictionOut])
def well_predictions(
    well_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return list_predictions(well_id=well_id, limit=limit, db=db, _=user)


@router.get("/anomalies", response_model=list[AnomalyOut])
def list_anomalies(
    well_id: int | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(AnomalyResult).options(joinedload(AnomalyResult.well))
    if well_id:
        q = q.filter(AnomalyResult.well_id == well_id)
    rows = q.order_by(AnomalyResult.calculated_at.desc()).limit(limit).all()
    return [
        AnomalyOut(
            id=r.id,
            well_id=r.well_id,
            well_name=r.well.name if r.well else None,
            calculated_at=r.calculated_at,
            algorithm=r.algorithm,
            anomaly_score=r.anomaly_score,
            is_anomaly=r.is_anomaly,
            window_start=r.window_start,
            window_end=r.window_end,
            details=r.details,
            features=r.features,
        )
        for r in rows
    ]


@router.get("/predictions/{prediction_id}", response_model=PredictionOut)
def get_prediction(
    prediction_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    r = (
        db.query(PredictionResult)
        .options(joinedload(PredictionResult.well))
        .filter(PredictionResult.id == prediction_id)
        .first()
    )
    if not r:
        raise HTTPException(status_code=404, detail="Прогноз не найден")
    return PredictionOut(
        id=r.id,
        well_id=r.well_id,
        well_name=r.well.name if r.well else None,
        calculated_at=r.calculated_at,
        model_name=r.model_name,
        model_version=r.model_version,
        failure_probability=r.failure_probability,
        risk_category=r.risk_category,
        horizon_days=r.horizon_days,
        top_factors=r.top_factors,
        presumed_failure_type=r.presumed_failure_type,
        is_reliable=r.is_reliable,
        reliability_note=r.reliability_note,
        features=r.features,
    )
