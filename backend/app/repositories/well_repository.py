from sqlalchemy.orm import Session, joinedload

from app.models import Well, WellPad


class WellRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, well_id: int) -> Well | None:
        return (
            self.db.query(Well)
            .options(joinedload(Well.well_pad).joinedload(WellPad.oil_field))
            .filter(Well.id == well_id)
            .first()
        )

    def list_all(self) -> list[Well]:
        return self.db.query(Well).order_by(Well.name).all()
