from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.constants import SENSOR_PARAM_SPECS
from app.models import Sensor, Telemetry, Well
from app.schemas.telemetry import TelemetryBatchIn


class TelemetryService:
    def __init__(self, db: Session):
        self.db = db

    def ingest(self, payload: TelemetryBatchIn) -> dict:
        well = self.db.query(Well).filter(Well.id == payload.well_id).first()
        if not well:
            raise LookupError("Скважина не найдена")

        sensors = (
            self.db.query(Sensor)
            .options(joinedload(Sensor.sensor_type))
            .filter(Sensor.well_id == payload.well_id)
            .all()
        )
        by_tag = {s.tag: s for s in sensors}
        by_id = {s.id: s for s in sensors}
        by_code = {s.sensor_type.code: s for s in sensors}

        accepted = skipped = rejected = 0
        errors: list[str] = []

        for idx, point in enumerate(payload.points):
            sensor = None
            if point.sensor_id:
                sensor = by_id.get(point.sensor_id)
            elif point.sensor_tag:
                sensor = by_tag.get(point.sensor_tag)
            elif point.parameter_code:
                sensor = by_code.get(point.parameter_code)
            if not sensor:
                rejected += 1
                errors.append(f"[{idx}] сенсор не найден")
                continue

            code = sensor.sensor_type.code
            spec = SENSOR_PARAM_SPECS.get(code, {})
            value = point.value
            quality = point.quality_flag
            vmin, vmax = spec.get("min"), spec.get("max")
            if vmin is not None and vmax is not None:
                if value < vmin * 0.3 or value > vmax * 2.0:
                    quality = "bad"
                elif value < vmin or value > vmax:
                    quality = "suspect"

            idem = point.idempotency_key or (
                f"{payload.batch_id}:{sensor.id}:{point.recorded_at.isoformat()}"
                if payload.batch_id
                else f"{sensor.id}:{point.recorded_at.isoformat()}"
            )

            nested = self.db.begin_nested()
            try:
                self.db.add(
                    Telemetry(
                        well_id=payload.well_id,
                        equipment_unit_id=sensor.equipment_unit_id,
                        sensor_id=sensor.id,
                        parameter_code=code,
                        value=value,
                        unit=sensor.sensor_type.unit,
                        quality_flag=quality,
                        source=point.source,
                        recorded_at=point.recorded_at,
                        idempotency_key=idem,
                    )
                )
                self.db.flush()
                nested.commit()
                accepted += 1
            except IntegrityError:
                nested.rollback()
                skipped += 1

        self.db.commit()
        return {
            "accepted": accepted,
            "skipped_duplicates": skipped,
            "rejected": rejected,
            "errors": errors[:50],
        }

    def query_series(
        self,
        *,
        well_id: int,
        parameter_codes: list[str] | None,
        date_from: datetime,
        date_to: datetime,
        limit: int = 5000,
    ) -> list[dict]:
        well = self.db.query(Well).filter(Well.id == well_id).first()
        if not well:
            raise LookupError("Скважина не найдена")
        if date_from > date_to:
            raise ValueError("Некорректный период")

        q = self.db.query(Telemetry).filter(
            Telemetry.well_id == well_id,
            Telemetry.recorded_at >= date_from,
            Telemetry.recorded_at <= date_to,
        )
        if parameter_codes:
            q = q.filter(Telemetry.parameter_code.in_(parameter_codes))
        rows = q.order_by(Telemetry.recorded_at.asc()).limit(limit).all()

        grouped: dict[str, dict] = {}
        for row in rows:
            bucket = grouped.setdefault(
                row.parameter_code,
                {"parameter_code": row.parameter_code, "unit": row.unit, "points": []},
            )
            bucket["points"].append(row)
        return list(grouped.values())
