from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.models import Failure, MaintenanceAction, Well
from app.schemas.events import FailureCreate, MaintenanceCreate


class EventService:
    def __init__(self, db: Session):
        self.db = db

    def list_failures(
        self,
        *,
        well_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 200,
    ) -> list[dict]:
        q = self.db.query(Failure).options(joinedload(Failure.well))
        if well_id:
            q = q.filter(Failure.well_id == well_id)
        if date_from:
            q = q.filter(Failure.occurred_at >= date_from)
        if date_to:
            q = q.filter(Failure.occurred_at <= date_to)
        rows = q.order_by(Failure.occurred_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "well_id": r.well_id,
                "well_name": r.well.name if r.well else None,
                "equipment_unit_id": r.equipment_unit_id,
                "failure_type": r.failure_type,
                "severity": r.severity,
                "occurred_at": r.occurred_at,
                "downtime_hours": r.downtime_hours,
                "presumed_cause": r.presumed_cause,
                "description": r.description,
            }
            for r in rows
        ]

    def create_failure(self, payload: FailureCreate, user_id: int | None) -> Failure:
        if not self.db.query(Well).filter(Well.id == payload.well_id).first():
            raise LookupError("Скважина не найдена")
        row = Failure(**payload.model_dump(), created_by_id=user_id)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_maintenance(
        self,
        *,
        well_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 200,
    ) -> list[dict]:
        q = self.db.query(MaintenanceAction).options(joinedload(MaintenanceAction.well))
        if well_id:
            q = q.filter(MaintenanceAction.well_id == well_id)
        if date_from:
            q = q.filter(MaintenanceAction.started_at >= date_from)
        if date_to:
            q = q.filter(MaintenanceAction.started_at <= date_to)
        rows = q.order_by(MaintenanceAction.started_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "well_id": r.well_id,
                "well_name": r.well.name if r.well else None,
                "equipment_unit_id": r.equipment_unit_id,
                "action_type": r.action_type,
                "started_at": r.started_at,
                "ended_at": r.ended_at,
                "performer": r.performer,
                "result": r.result,
                "description": r.description,
            }
            for r in rows
        ]

    def create_maintenance(self, payload: MaintenanceCreate, user_id: int | None) -> MaintenanceAction:
        if not self.db.query(Well).filter(Well.id == payload.well_id).first():
            raise LookupError("Скважина не найдена")
        if payload.ended_at and payload.ended_at < payload.started_at:
            raise ValueError("Дата окончания раньше даты начала")
        row = MaintenanceAction(**payload.model_dump(), created_by_id=user_id)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_combined_events(
        self,
        *,
        well_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 100,
    ) -> list[dict]:
        events: list[dict] = []
        for f in self.list_failures(well_id=well_id, date_from=date_from, date_to=date_to, limit=limit):
            events.append(
                {
                    "id": f["id"],
                    "event_kind": "failure",
                    "well_id": f["well_id"],
                    "well_name": f["well_name"],
                    "title": f["failure_type"],
                    "occurred_at": f["occurred_at"],
                    "severity": f["severity"],
                    "description": f["description"],
                }
            )
        for m in self.list_maintenance(well_id=well_id, date_from=date_from, date_to=date_to, limit=limit):
            events.append(
                {
                    "id": m["id"],
                    "event_kind": "maintenance",
                    "well_id": m["well_id"],
                    "well_name": m["well_name"],
                    "title": m["action_type"],
                    "occurred_at": m["started_at"],
                    "severity": None,
                    "description": m["description"],
                }
            )
        events.sort(key=lambda e: e["occurred_at"], reverse=True)
        return events[:limit]
