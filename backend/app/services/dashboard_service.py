from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Alert, Well
from app.services.alert_service import AlertService
from app.services.event_service import EventService
from app.services.well_service import WellService


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard(self) -> dict:
        wells = WellService(self.db).list_wells(page=1, page_size=500)["items"]
        total = len(wells)
        normal = sum(1 for w in wells if w["status"] == "normal")
        warning = sum(1 for w in wells if w["status"] == "warning")
        critical = sum(1 for w in wells if w["status"] == "critical")
        stopped = sum(1 for w in wells if w["status"] in {"stopped", "maintenance"})

        risk = {"low": 0, "medium": 0, "high": 0, "unknown": 0}
        for w in wells:
            key = w.get("risk_category") or "unknown"
            if key not in risk:
                key = "unknown"
            risk[key] += 1

        active_alerts = (
            self.db.query(func.count(Alert.id)).filter(Alert.status == "new").scalar() or 0
        )
        attention = [
            w
            for w in wells
            if w.get("risk_category") in {"medium", "high"}
            or w["status"] in {"warning", "critical"}
            or w.get("active_alerts", 0) > 0
        ]
        attention.sort(
            key=lambda w: (
                0 if w.get("risk_category") == "high" else 1,
                -(w.get("failure_probability") or 0),
            )
        )

        recent_events = EventService(self.db).list_combined_events(limit=10)
        recent_alerts = AlertService(self.db).list_alerts(page=1, page_size=8, status="new")[
            "items"
        ]

        return {
            "total_wells": total,
            "normal_count": normal,
            "warning_count": warning,
            "critical_count": critical,
            "stopped_count": stopped,
            "active_alerts": active_alerts,
            "risk_distribution": risk,
            "attention_wells": attention[:10],
            "recent_events": recent_events,
            "recent_alerts": recent_alerts,
            "generated_at": datetime.now(timezone.utc),
        }
