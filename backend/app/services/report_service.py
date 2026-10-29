from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.models import (
    Alert,
    AnomalyResult,
    Failure,
    MaintenanceAction,
    PredictionResult,
    Report,
    Telemetry,
    Well,
)
from app.schemas.reports import ReportCreate
from app.services.well_service import WellService


REPORTS_DIR = Path("/tmp/gno_reports")


class ReportService:
    def __init__(self, db: Session):
        self.db = db
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def list_reports(self, limit: int = 100) -> list[Report]:
        return (
            self.db.query(Report)
            .order_by(Report.created_at.desc())
            .limit(limit)
            .all()
        )

    def get(self, report_id: int) -> Report | None:
        return self.db.query(Report).filter(Report.id == report_id).first()

    def create(self, payload: ReportCreate, user_id: int | None) -> Report:
        if payload.period_start > payload.period_end:
            raise ValueError("Некорректный период отчёта")

        content = self._build_content(payload)
        title = self._title(payload, content)
        text = self._to_text(content)
        file_path = None
        file_format = payload.export_format or "json"

        report = Report(
            report_type=payload.report_type,
            title=title,
            period_start=payload.period_start,
            period_end=payload.period_end,
            parameters=payload.model_dump(mode="json"),
            content_json=content,
            content_text=text,
            file_format=file_format,
            created_by_id=user_id,
        )
        self.db.add(report)
        self.db.flush()

        if file_format == "csv":
            file_path = self._write_csv(report.id, content)
        elif file_format == "pdf":
            file_path = self._write_pdf(report.id, title, text)
        report.file_path = file_path
        self.db.commit()
        self.db.refresh(report)
        return report

    def _title(self, payload: ReportCreate, content: dict[str, Any]) -> str:
        labels = {
            "fund_summary": "Сводка по фонду скважин",
            "well": "Отчёт по скважине",
            "telemetry": "Отчёт по телеметрии",
            "failures": "Отчёт по отказам и ремонтам",
            "analytics": "Отчёт по аномалиям и прогнозам",
            "alerts": "Отчёт по уведомлениям",
        }
        base = labels.get(payload.report_type, "Отчёт")
        if payload.well_id:
            well = self.db.query(Well).filter(Well.id == payload.well_id).first()
            if well:
                return f"{base}: {well.name}"
        return base

    def _build_content(self, payload: ReportCreate) -> dict[str, Any]:
        start, end = payload.period_start, payload.period_end
        if payload.report_type == "fund_summary":
            wells = WellService(self.db).list_wells(page=1, page_size=500)["items"]
            return {
                "type": "fund_summary",
                "wells_total": len(wells),
                "by_status": self._count_by(wells, "status"),
                "by_risk": self._count_by(wells, "risk_category"),
                "wells": wells,
            }
        if payload.report_type == "well":
            if not payload.well_id:
                raise ValueError("Для отчёта по скважине укажите well_id")
            well = self.db.query(Well).filter(Well.id == payload.well_id).first()
            if not well:
                raise LookupError("Скважина не найдена")
            return {
                "type": "well",
                "well": {"id": well.id, "name": well.name, "status": well.status},
                "failures": self._failures(payload.well_id, start, end),
                "maintenance": self._maintenance(payload.well_id, start, end),
                "predictions": self._predictions(payload.well_id, start, end),
                "alerts": self._alerts(payload.well_id, start, end),
            }
        if payload.report_type == "telemetry":
            if not payload.well_id:
                raise ValueError("Для отчёта по телеметрии укажите well_id")
            rows = (
                self.db.query(Telemetry)
                .filter(
                    Telemetry.well_id == payload.well_id,
                    Telemetry.recorded_at >= start,
                    Telemetry.recorded_at <= end,
                )
                .order_by(Telemetry.recorded_at.asc())
                .limit(5000)
                .all()
            )
            return {
                "type": "telemetry",
                "count": len(rows),
                "points": [
                    {
                        "parameter_code": r.parameter_code,
                        "value": r.value,
                        "unit": r.unit,
                        "recorded_at": r.recorded_at.isoformat(),
                    }
                    for r in rows
                ],
            }
        if payload.report_type == "failures":
            return {
                "type": "failures",
                "failures": self._failures(payload.well_id, start, end),
                "maintenance": self._maintenance(payload.well_id, start, end),
            }
        if payload.report_type == "analytics":
            return {
                "type": "analytics",
                "anomalies": self._anomalies(payload.well_id, start, end),
                "predictions": self._predictions(payload.well_id, start, end),
            }
        if payload.report_type == "alerts":
            return {"type": "alerts", "alerts": self._alerts(payload.well_id, start, end)}
        raise ValueError("Неизвестный тип отчёта")

    def _failures(self, well_id, start, end):
        q = self.db.query(Failure).filter(Failure.occurred_at >= start, Failure.occurred_at <= end)
        if well_id:
            q = q.filter(Failure.well_id == well_id)
        return [
            {
                "id": r.id,
                "well_id": r.well_id,
                "failure_type": r.failure_type,
                "severity": r.severity,
                "occurred_at": r.occurred_at.isoformat(),
            }
            for r in q.order_by(Failure.occurred_at.desc()).limit(500).all()
        ]

    def _maintenance(self, well_id, start, end):
        q = self.db.query(MaintenanceAction).filter(
            MaintenanceAction.started_at >= start, MaintenanceAction.started_at <= end
        )
        if well_id:
            q = q.filter(MaintenanceAction.well_id == well_id)
        return [
            {
                "id": r.id,
                "well_id": r.well_id,
                "action_type": r.action_type,
                "started_at": r.started_at.isoformat(),
                "result": r.result,
            }
            for r in q.order_by(MaintenanceAction.started_at.desc()).limit(500).all()
        ]

    def _predictions(self, well_id, start, end):
        q = self.db.query(PredictionResult).filter(
            PredictionResult.calculated_at >= start, PredictionResult.calculated_at <= end
        )
        if well_id:
            q = q.filter(PredictionResult.well_id == well_id)
        return [
            {
                "id": r.id,
                "well_id": r.well_id,
                "failure_probability": r.failure_probability,
                "risk_category": r.risk_category,
                "calculated_at": r.calculated_at.isoformat(),
                "is_reliable": r.is_reliable,
            }
            for r in q.order_by(PredictionResult.calculated_at.desc()).limit(500).all()
        ]

    def _anomalies(self, well_id, start, end):
        q = self.db.query(AnomalyResult).filter(
            AnomalyResult.calculated_at >= start, AnomalyResult.calculated_at <= end
        )
        if well_id:
            q = q.filter(AnomalyResult.well_id == well_id)
        return [
            {
                "id": r.id,
                "well_id": r.well_id,
                "anomaly_score": r.anomaly_score,
                "is_anomaly": r.is_anomaly,
                "calculated_at": r.calculated_at.isoformat(),
            }
            for r in q.order_by(AnomalyResult.calculated_at.desc()).limit(500).all()
        ]

    def _alerts(self, well_id, start, end):
        q = self.db.query(Alert).filter(Alert.created_at >= start, Alert.created_at <= end)
        if well_id:
            q = q.filter(Alert.well_id == well_id)
        return [
            {
                "id": r.id,
                "well_id": r.well_id,
                "alert_type": r.alert_type,
                "severity": r.severity,
                "status": r.status,
                "message": r.message,
                "created_at": r.created_at.isoformat(),
            }
            for r in q.order_by(Alert.created_at.desc()).limit(500).all()
        ]

    @staticmethod
    def _count_by(items: list[dict], key: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for item in items:
            k = str(item.get(key) or "unknown")
            out[k] = out.get(k, 0) + 1
        return out

    @staticmethod
    def _to_text(content: dict[str, Any]) -> str:
        return json.dumps(content, ensure_ascii=False, indent=2, default=str)

    def _write_csv(self, report_id: int, content: dict[str, Any]) -> str:
        path = REPORTS_DIR / f"report_{report_id}.csv"
        rows: list[dict[str, Any]] = []
        for key in ("wells", "failures", "maintenance", "predictions", "anomalies", "alerts", "points"):
            if isinstance(content.get(key), list) and content[key]:
                rows = content[key]
                break
        if not rows:
            rows = [{"summary": json.dumps(content, ensure_ascii=False, default=str)}]
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return str(path)

    def _write_pdf(self, report_id: int, title: str, text: str) -> str:
        path = REPORTS_DIR / f"report_{report_id}.pdf"
        c = canvas.Canvas(str(path), pagesize=A4)
        width, height = A4
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, height - 40, title[:90])
        c.setFont("Helvetica", 9)
        y = height - 70
        for line in text.splitlines()[:80]:
            c.drawString(40, y, line[:110])
            y -= 12
            if y < 40:
                c.showPage()
                c.setFont("Helvetica", 9)
                y = height - 40
        c.save()
        return str(path)
