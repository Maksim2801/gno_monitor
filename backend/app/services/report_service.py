from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.core.constants import SENSOR_PARAM_SPECS
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

STATUS_LABELS = {
    "normal": "Норма",
    "warning": "Предупреждение",
    "critical": "Критично",
    "stopped": "Остановлена",
    "maintenance": "Ремонт",
}
RISK_LABELS = {
    "low": "Низкий",
    "medium": "Средний",
    "high": "Высокий",
}
SEVERITY_LABELS = {
    "info": "Информация",
    "warning": "Предупреждение",
    "critical": "Критично",
}
ALERT_STATUS_LABELS = {
    "new": "Новое",
    "acknowledged": "Принято",
    "closed": "Закрыто",
}

_PDF_FONTS_READY = False


def _register_pdf_fonts() -> tuple[str, str]:
    global _PDF_FONTS_READY
    regular = "Helvetica"
    bold = "Helvetica-Bold"
    candidates = [
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
        (
            Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
        ),
        (
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/arialbd.ttf"),
        ),
    ]
    for regular_path, bold_path in candidates:
        if regular_path.exists() and bold_path.exists():
            if not _PDF_FONTS_READY:
                pdfmetrics.registerFont(TTFont("GnoSans", str(regular_path)))
                pdfmetrics.registerFont(TTFont("GnoSans-Bold", str(bold_path)))
                _PDF_FONTS_READY = True
            return "GnoSans", "GnoSans-Bold"
    return regular, bold


def _label(mapping: dict[str, str], value: Any, default: str | None = None) -> str:
    key = str(value or "")
    return mapping.get(key, default if default is not None else (key or "—"))


def _param_name(code: str | None) -> str:
    if not code:
        return "—"
    spec = SENSOR_PARAM_SPECS.get(code)
    return spec["name"] if spec else code


def _format_dt(value: Any) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return str(value)
    if dt.tzinfo is not None:
        dt = dt.astimezone()
    return dt.strftime("%d.%m.%Y %H:%M")


def _format_number(value: Any, digits: int = 2) -> str:
    if value is None or value == "":
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.{digits}f}".rstrip("0").rstrip(".")


def _yes_no(value: Any) -> str:
    return "Да" if bool(value) else "Нет"


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
        text = self._to_text(title, payload, content)
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

    def _well_name(self, well_id: Any) -> str:
        if well_id is None:
            return "—"
        well = self.db.query(Well).filter(Well.id == well_id).first()
        return well.name if well else str(well_id)

    def _to_text(self, title: str, payload: ReportCreate, content: dict[str, Any]) -> str:
        lines = [
            title,
            f"Период: {_format_dt(payload.period_start)} — {_format_dt(payload.period_end)}",
            "",
        ]
        report_type = content.get("type")

        if report_type == "fund_summary":
            lines.append(f"Всего скважин: {content.get('wells_total', 0)}")
            lines.append("По статусу:")
            for key, value in (content.get("by_status") or {}).items():
                lines.append(f"  • {_label(STATUS_LABELS, key)}: {value}")
            lines.append("По категории риска:")
            for key, value in (content.get("by_risk") or {}).items():
                lines.append(f"  • {_label(RISK_LABELS, key, 'н/д')}: {value}")
            lines.append("")
            lines.append("Скважины:")
            for well in content.get("wells") or []:
                lines.append(
                    "  • {name}: статус {status}, риск {risk}".format(
                        name=well.get("name") or f"#{well.get('id')}",
                        status=_label(STATUS_LABELS, well.get("status")),
                        risk=_label(RISK_LABELS, well.get("risk_category"), "н/д"),
                    )
                )

        elif report_type == "well":
            well = content.get("well") or {}
            lines.append(
                f"Скважина: {well.get('name', '—')} (статус: {_label(STATUS_LABELS, well.get('status'))})"
            )
            lines.extend(self._section_failures(content.get("failures") or []))
            lines.extend(self._section_maintenance(content.get("maintenance") or []))
            lines.extend(self._section_predictions(content.get("predictions") or []))
            lines.extend(self._section_alerts(content.get("alerts") or []))

        elif report_type == "telemetry":
            points = content.get("points") or []
            lines.append(f"Записей телеметрии: {content.get('count', len(points))}")
            lines.append("")
            for point in points[:200]:
                lines.append(
                    "{dt} — {name}: {value} {unit}".format(
                        dt=_format_dt(point.get("recorded_at")),
                        name=_param_name(point.get("parameter_code")),
                        value=_format_number(point.get("value")),
                        unit=point.get("unit") or "",
                    ).rstrip()
                )
            if len(points) > 200:
                lines.append(f"... и ещё {len(points) - 200} записей")

        elif report_type == "failures":
            lines.extend(self._section_failures(content.get("failures") or []))
            lines.extend(self._section_maintenance(content.get("maintenance") or []))

        elif report_type == "analytics":
            lines.extend(self._section_anomalies(content.get("anomalies") or []))
            lines.extend(self._section_predictions(content.get("predictions") or []))

        elif report_type == "alerts":
            lines.extend(self._section_alerts(content.get("alerts") or []))

        else:
            lines.append(json.dumps(content, ensure_ascii=False, indent=2, default=str))

        return "\n".join(lines).strip() + "\n"

    def _section_failures(self, rows: list[dict[str, Any]]) -> list[str]:
        lines = ["", f"Отказы ({len(rows)}):"]
        if not rows:
            lines.append("  нет данных за период")
            return lines
        for row in rows[:100]:
            lines.append(
                "  • {dt} | скважина {well} | {ftype} | {sev}".format(
                    dt=_format_dt(row.get("occurred_at")),
                    well=self._well_name(row.get("well_id")),
                    ftype=row.get("failure_type") or "—",
                    sev=_label(SEVERITY_LABELS, row.get("severity")),
                )
            )
        return lines

    def _section_maintenance(self, rows: list[dict[str, Any]]) -> list[str]:
        lines = ["", f"Ремонтные работы ({len(rows)}):"]
        if not rows:
            lines.append("  нет данных за период")
            return lines
        for row in rows[:100]:
            lines.append(
                "  • {dt} | скважина {well} | {action} | результат: {result}".format(
                    dt=_format_dt(row.get("started_at")),
                    well=self._well_name(row.get("well_id")),
                    action=row.get("action_type") or "—",
                    result=row.get("result") or "—",
                )
            )
        return lines

    def _section_predictions(self, rows: list[dict[str, Any]]) -> list[str]:
        lines = ["", f"Прогнозы отказа ({len(rows)}):"]
        if not rows:
            lines.append("  нет данных за период")
            return lines
        for row in rows[:100]:
            prob = row.get("failure_probability")
            lines.append(
                "  • {dt} | скважина {well} | вероятность {prob}% | риск {risk} | надёжность: {rel}".format(
                    dt=_format_dt(row.get("calculated_at")),
                    well=self._well_name(row.get("well_id")),
                    prob=_format_number((prob or 0) * 100, 1),
                    risk=_label(RISK_LABELS, row.get("risk_category"), "н/д"),
                    rel=_yes_no(row.get("is_reliable")),
                )
            )
        return lines

    def _section_anomalies(self, rows: list[dict[str, Any]]) -> list[str]:
        lines = ["", f"Аномалии ({len(rows)}):"]
        if not rows:
            lines.append("  нет данных за период")
            return lines
        for row in rows[:100]:
            lines.append(
                "  • {dt} | скважина {well} | оценка {score} | аномалия: {flag}".format(
                    dt=_format_dt(row.get("calculated_at")),
                    well=self._well_name(row.get("well_id")),
                    score=_format_number(row.get("anomaly_score"), 3),
                    flag=_yes_no(row.get("is_anomaly")),
                )
            )
        return lines

    def _section_alerts(self, rows: list[dict[str, Any]]) -> list[str]:
        lines = ["", f"Уведомления ({len(rows)}):"]
        if not rows:
            lines.append("  нет данных за период")
            return lines
        for row in rows[:100]:
            lines.append(
                "  • {dt} | скважина {well} | {sev} | {status} | {message}".format(
                    dt=_format_dt(row.get("created_at")),
                    well=self._well_name(row.get("well_id")),
                    sev=_label(SEVERITY_LABELS, row.get("severity")),
                    status=_label(ALERT_STATUS_LABELS, row.get("status")),
                    message=(row.get("message") or "—").replace("\n", " "),
                )
            )
        return lines

    def _csv_rows(self, content: dict[str, Any]) -> list[dict[str, Any]]:
        report_type = content.get("type")
        if report_type == "fund_summary":
            return [
                {
                    "Скважина": well.get("name") or f"#{well.get('id')}",
                    "Статус": _label(STATUS_LABELS, well.get("status")),
                    "Категория риска": _label(RISK_LABELS, well.get("risk_category"), "н/д"),
                    "Месторождение": well.get("oil_field") or "—",
                }
                for well in content.get("wells") or []
            ]
        if report_type == "telemetry":
            return [
                {
                    "Дата и время": _format_dt(point.get("recorded_at")),
                    "Параметр": _param_name(point.get("parameter_code")),
                    "Значение": _format_number(point.get("value")),
                    "Единица": point.get("unit") or "",
                }
                for point in content.get("points") or []
            ]
        if report_type in {"well", "failures"}:
            rows: list[dict[str, Any]] = []
            for row in content.get("failures") or []:
                rows.append(
                    {
                        "Раздел": "Отказ",
                        "Дата и время": _format_dt(row.get("occurred_at")),
                        "Скважина": self._well_name(row.get("well_id")),
                        "Описание": row.get("failure_type") or "—",
                        "Важность": _label(SEVERITY_LABELS, row.get("severity")),
                        "Дополнительно": "",
                    }
                )
            for row in content.get("maintenance") or []:
                rows.append(
                    {
                        "Раздел": "Ремонт",
                        "Дата и время": _format_dt(row.get("started_at")),
                        "Скважина": self._well_name(row.get("well_id")),
                        "Описание": row.get("action_type") or "—",
                        "Важность": "",
                        "Дополнительно": row.get("result") or "",
                    }
                )
            if report_type == "well":
                for row in content.get("predictions") or []:
                    rows.append(
                        {
                            "Раздел": "Прогноз",
                            "Дата и время": _format_dt(row.get("calculated_at")),
                            "Скважина": self._well_name(row.get("well_id")),
                            "Описание": f"Вероятность отказа {_format_number((row.get('failure_probability') or 0) * 100, 1)}%",
                            "Важность": _label(RISK_LABELS, row.get("risk_category"), "н/д"),
                            "Дополнительно": f"Надёжность: {_yes_no(row.get('is_reliable'))}",
                        }
                    )
                for row in content.get("alerts") or []:
                    rows.append(
                        {
                            "Раздел": "Уведомление",
                            "Дата и время": _format_dt(row.get("created_at")),
                            "Скважина": self._well_name(row.get("well_id")),
                            "Описание": row.get("message") or "—",
                            "Важность": _label(SEVERITY_LABELS, row.get("severity")),
                            "Дополнительно": _label(ALERT_STATUS_LABELS, row.get("status")),
                        }
                    )
            return rows
        if report_type == "analytics":
            rows = []
            for row in content.get("anomalies") or []:
                rows.append(
                    {
                        "Раздел": "Аномалия",
                        "Дата и время": _format_dt(row.get("calculated_at")),
                        "Скважина": self._well_name(row.get("well_id")),
                        "Описание": f"Оценка {_format_number(row.get('anomaly_score'), 3)}",
                        "Важность": "",
                        "Дополнительно": f"Аномалия: {_yes_no(row.get('is_anomaly'))}",
                    }
                )
            for row in content.get("predictions") or []:
                rows.append(
                    {
                        "Раздел": "Прогноз",
                        "Дата и время": _format_dt(row.get("calculated_at")),
                        "Скважина": self._well_name(row.get("well_id")),
                        "Описание": f"Вероятность отказа {_format_number((row.get('failure_probability') or 0) * 100, 1)}%",
                        "Важность": _label(RISK_LABELS, row.get("risk_category"), "н/д"),
                        "Дополнительно": f"Надёжность: {_yes_no(row.get('is_reliable'))}",
                    }
                )
            return rows
        if report_type == "alerts":
            return [
                {
                    "Дата и время": _format_dt(row.get("created_at")),
                    "Скважина": self._well_name(row.get("well_id")),
                    "Тип": row.get("alert_type") or "—",
                    "Важность": _label(SEVERITY_LABELS, row.get("severity")),
                    "Статус": _label(ALERT_STATUS_LABELS, row.get("status")),
                    "Сообщение": row.get("message") or "—",
                }
                for row in content.get("alerts") or []
            ]
        return [{"Содержимое": json.dumps(content, ensure_ascii=False, default=str)}]

    def _write_csv(self, report_id: int, content: dict[str, Any]) -> str:
        path = REPORTS_DIR / f"report_{report_id}.csv"
        rows = self._csv_rows(content)
        if not rows:
            rows = [{"Сообщение": "Нет данных за выбранный период"}]
        fieldnames = list(rows[0].keys())
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        return str(path)

    def _write_pdf(self, report_id: int, title: str, text: str) -> str:
        path = REPORTS_DIR / f"report_{report_id}.pdf"
        font_regular, font_bold = _register_pdf_fonts()
        c = canvas.Canvas(str(path), pagesize=A4)
        width, height = A4
        margin_x = 40
        y = height - 40
        max_chars = 95

        def new_page() -> None:
            nonlocal y
            c.showPage()
            c.setFont(font_regular, 10)
            y = height - 40

        c.setFont(font_bold, 14)
        for chunk_start in range(0, max(len(title), 1), 70):
            c.drawString(margin_x, y, title[chunk_start : chunk_start + 70])
            y -= 18
            if y < 50:
                new_page()

        y -= 6
        c.setFont(font_regular, 10)
        for raw_line in text.splitlines():
            line = raw_line if raw_line.strip() else " "
            while line:
                part = line[:max_chars]
                c.drawString(margin_x, y, part)
                line = line[max_chars:]
                y -= 14
                if y < 40:
                    new_page()
        c.save()
        return str(path)
