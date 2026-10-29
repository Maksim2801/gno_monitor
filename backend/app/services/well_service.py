from math import ceil

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models import Alert, OilField, PredictionResult, Well, WellPad
from app.schemas.wells import WellCreate, WellUpdate


class WellService:
    def __init__(self, db: Session):
        self.db = db

    def list_wells(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        status: str | None = None,
        oil_field_id: int | None = None,
        risk_category: str | None = None,
        sort_by: str = "name",
        sort_dir: str = "asc",
    ) -> dict:
        q = (
            self.db.query(Well)
            .join(Well.well_pad)
            .join(WellPad.oil_field)
            .options(joinedload(Well.well_pad).joinedload(WellPad.oil_field))
        )
        if search:
            like = f"%{search.lower()}%"
            q = q.filter(
                or_(
                    func.lower(Well.name).like(like),
                    func.lower(func.coalesce(Well.inventory_number, "")).like(like),
                )
            )

        if status:
            q = q.filter(Well.status == status)
        if oil_field_id:
            q = q.filter(WellPad.oil_field_id == oil_field_id)

        total = q.count()
        sort_col = {
            "name": Well.name,
            "status": Well.status,
            "id": Well.id,
        }.get(sort_by, Well.name)
        q = q.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())
        wells = q.offset((page - 1) * page_size).limit(page_size).all()

        items = []
        for well in wells:
            latest_pred = (
                self.db.query(PredictionResult)
                .filter(PredictionResult.well_id == well.id)
                .order_by(PredictionResult.calculated_at.desc())
                .first()
            )
            if risk_category and (
                not latest_pred or latest_pred.risk_category != risk_category
            ):
                continue
            active_alerts = (
                self.db.query(func.count(Alert.id))
                .filter(Alert.well_id == well.id, Alert.status == "new")
                .scalar()
                or 0
            )
            items.append(
                {
                    "id": well.id,
                    "name": well.name,
                    "inventory_number": well.inventory_number,
                    "status": well.status,
                    "depth_m": well.depth_m,
                    "oil_field": well.well_pad.oil_field.name,
                    "well_pad": well.well_pad.name,
                    "risk_category": latest_pred.risk_category if latest_pred else None,
                    "failure_probability": (
                        latest_pred.failure_probability if latest_pred else None
                    ),
                    "active_alerts": active_alerts,
                }
            )

        # If risk filter applied after fetch, recompute totals loosely
        if risk_category:
            total = len(items)

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": max(ceil(total / page_size), 1) if total else 0,
        }

    def get_well(self, well_id: int) -> Well | None:
        return (
            self.db.query(Well)
            .options(
                joinedload(Well.well_pad).joinedload(WellPad.oil_field),
                joinedload(Well.equipment_units),
                joinedload(Well.sensors),
            )
            .filter(Well.id == well_id)
            .first()
        )

    def create_well(self, payload: WellCreate) -> Well:
        pad = self.db.query(WellPad).filter(WellPad.id == payload.well_pad_id).first()
        if not pad:
            raise LookupError("Куст не найден")
        if self.db.query(Well).filter(Well.name == payload.name).first():
            raise ValueError("Скважина с таким именем уже существует")
        well = Well(**payload.model_dump())
        self.db.add(well)
        self.db.commit()
        self.db.refresh(well)
        return well

    def update_well(self, well_id: int, payload: WellUpdate) -> Well:
        well = self.db.query(Well).filter(Well.id == well_id).first()
        if not well:
            raise LookupError("Скважина не найдена")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(well, key, value)
        self.db.commit()
        self.db.refresh(well)
        return well

    def list_fields(self) -> list[OilField]:
        return self.db.query(OilField).order_by(OilField.name).all()

    def list_pads(self, oil_field_id: int | None = None) -> list[WellPad]:
        q = self.db.query(WellPad).options(joinedload(WellPad.oil_field))
        if oil_field_id:
            q = q.filter(WellPad.oil_field_id == oil_field_id)
        return q.order_by(WellPad.name).all()
