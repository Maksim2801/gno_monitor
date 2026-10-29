from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_write
from app.db.session import get_db
from app.models import User
from app.schemas.telemetry import TelemetryBatchIn, TelemetryIngestResult, TelemetrySeriesOut
from app.services.telemetry_service import TelemetryService

router = APIRouter()


@router.post("", response_model=TelemetryIngestResult)
def ingest_telemetry(
    payload: TelemetryBatchIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_write),
):
    try:
        return TelemetryService(db).ingest(payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/wells/{well_id}", response_model=list[TelemetrySeriesOut])
def get_well_telemetry(
    well_id: int,
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    parameters: str | None = Query(None, description="Comma-separated parameter codes"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    codes = [p.strip() for p in parameters.split(",")] if parameters else None
    try:
        return TelemetryService(db).query_series(
            well_id=well_id,
            parameter_codes=codes,
            date_from=date_from,
            date_to=date_to,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/import/csv", response_model=TelemetryIngestResult)
async def import_csv(
    well_id: int = Query(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_write),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Ожидается CSV-файл")
    raw = await file.read()
    if len(raw) > 5_000_000:
        raise HTTPException(status_code=400, detail="Файл слишком большой (макс. 5 МБ)")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Файл должен быть в UTF-8") from exc

    import csv
    import io
    from datetime import datetime as dt

    reader = csv.DictReader(io.StringIO(text))
    required = {"parameter_code", "value", "recorded_at"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise HTTPException(
            status_code=400,
            detail="CSV должен содержать колонки: parameter_code,value,recorded_at",
        )

    points = []
    for row in reader:
        try:
            points.append(
                {
                    "parameter_code": row["parameter_code"].strip(),
                    "value": float(row["value"]),
                    "recorded_at": dt.fromisoformat(row["recorded_at"].replace("Z", "+00:00")),
                    "source": "csv",
                    "idempotency_key": row.get("idempotency_key") or None,
                }
            )
        except Exception:
            continue
    if not points:
        raise HTTPException(status_code=400, detail="В CSV нет корректных строк")

    payload = TelemetryBatchIn(well_id=well_id, points=points, batch_id=file.filename)
    try:
        return TelemetryService(db).ingest(payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
