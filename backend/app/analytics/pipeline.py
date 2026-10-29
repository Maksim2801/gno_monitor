"""End-to-end analytics pipeline for wells."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from app.analytics.anomaly import AnomalyDetector
from app.analytics.features import (
    FEATURE_PARAMS,
    build_feature_vector,
    feature_dict_to_vector,
    telemetry_to_dataframe,
)
from app.analytics.prediction import FailureRiskPredictor
from app.core.config import get_settings
from app.core.constants import (
    ALERT_STATUS_NEW,
    ALERT_TYPE_ANOMALY,
    ALERT_TYPE_FAILURE_RISK,
    ALERT_TYPE_THRESHOLD,
    ANALYTICS_VERSION,
    ANOMALY_ALGORITHM,
    FEATURE_LOOKBACK_HOURS,
    MIN_POINTS_FOR_ANALYTICS,
    PREDICTION_MODEL,
    RISK_HIGH,
    RISK_MEDIUM,
    SEVERITY_CRITICAL,
    SEVERITY_WARNING,
    WELL_STATUS_CRITICAL,
    WELL_STATUS_NORMAL,
    WELL_STATUS_WARNING,
    WINDOW_HOURS,
)
from app.models import (
    Alert,
    AnomalyResult,
    Failure,
    MaintenanceAction,
    MlModel,
    PredictionResult,
    Telemetry,
    Well,
)


class AnalyticsPipeline:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.anomaly_detector = AnomalyDetector()
        self.predictor = FailureRiskPredictor()

    def run(self, well_ids: list[int] | None = None) -> dict[str, int | str]:
        wells_q = self.db.query(Well)
        if well_ids:
            wells_q = wells_q.filter(Well.id.in_(well_ids))
        wells = wells_q.all()

        training = self._prepare_training_set(wells)
        self.anomaly_detector.fit(training["matrix"], training["columns"])
        fit_info = self.predictor.fit(
            training["matrix"], training["labels"], training["columns"]
        )
        self._upsert_ml_registry(fit_info)

        stats = {
            "wells_processed": 0,
            "anomalies_created": 0,
            "predictions_created": 0,
            "alerts_created": 0,
            "skipped_insufficient_data": 0,
        }

        for well in wells:
            result = self._process_well(well, training["columns"])
            if result is None:
                stats["skipped_insufficient_data"] += 1
                continue
            stats["wells_processed"] += 1
            stats["anomalies_created"] += result["anomaly"]
            stats["predictions_created"] += result["prediction"]
            stats["alerts_created"] += result["alerts"]

        self.db.commit()
        stats["message"] = (
            f"Аналитика завершена. RF trained={fit_info.get('trained')}, "
            f"samples={fit_info.get('samples', 0)}"
        )
        return stats

    def _prepare_training_set(self, wells: list[Well]) -> dict[str, Any]:
        feature_rows: list[dict[str, float]] = []
        labels: list[int] = []
        now = datetime.now(timezone.utc)

        for well in wells:
            rows = self._load_telemetry_rows(well.id, hours=FEATURE_LOOKBACK_HOURS + 24 * 14)
            df = telemetry_to_dataframe(rows)
            if df.empty:
                continue
            failures = (
                self.db.query(Failure)
                .filter(Failure.well_id == well.id)
                .order_by(Failure.occurred_at.asc())
                .all()
            )
            # Sliding windows every 12 hours over available history
            end_times = sorted(df["recorded_at"].unique())
            if len(end_times) < MIN_POINTS_FOR_ANALYTICS:
                continue
            step = max(len(end_times) // 20, 1)
            for ts in end_times[::step]:
                end = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
                ctx = self._context_counts(well.id, end)
                feats = build_feature_vector(
                    df,
                    window_end=end,
                    failures_count_30d=ctx["failures_30d"],
                    hours_since_maintenance=ctx["hours_since_maintenance"],
                    operating_hours=ctx["operating_hours"],
                )
                if not feats or feats.get("point_count", 0) < MIN_POINTS_FOR_ANALYTICS:
                    continue
                label = 0
                horizon_end = end + timedelta(days=self.settings.prediction_horizon_days)
                for f in failures:
                    fo = f.occurred_at
                    if fo.tzinfo is None:
                        fo = fo.replace(tzinfo=timezone.utc)
                    fo_naive = fo.astimezone(timezone.utc).replace(tzinfo=None)
                    end_naive = end if end.tzinfo is None else end.astimezone(timezone.utc).replace(tzinfo=None)
                    he_naive = horizon_end if horizon_end.tzinfo is None else horizon_end.astimezone(timezone.utc).replace(tzinfo=None)
                    if end_naive < fo_naive <= he_naive:
                        label = 1
                        break
                feature_rows.append(feats)
                labels.append(label)

        if not feature_rows:
            return {"matrix": np.empty((0, 0)), "labels": np.array([]), "columns": []}

        columns = sorted(feature_rows[0].keys())
        matrix = np.array([[row.get(c, 0.0) for c in columns] for row in feature_rows], dtype=float)
        return {"matrix": matrix, "labels": np.array(labels, dtype=int), "columns": columns}

    def _process_well(self, well: Well, columns: list[str]) -> dict[str, int] | None:
        now = datetime.now(timezone.utc)
        rows = self._load_telemetry_rows(well.id, hours=FEATURE_LOOKBACK_HOURS)
        df = telemetry_to_dataframe(rows)
        if df.empty or len(df) < MIN_POINTS_FOR_ANALYTICS:
            return None

        ctx = self._context_counts(well.id, now)
        features = build_feature_vector(
            df,
            window_end=now.replace(tzinfo=None),
            failures_count_30d=ctx["failures_30d"],
            hours_since_maintenance=ctx["hours_since_maintenance"],
            operating_hours=ctx["operating_hours"],
        )
        if not features or features.get("point_count", 0) < MIN_POINTS_FOR_ANALYTICS:
            return None

        if columns:
            vector, _ = feature_dict_to_vector(features, columns)
        else:
            vector, columns = feature_dict_to_vector(features)

        anomaly = self.anomaly_detector.assess(vector, features)
        prediction = self.predictor.predict(vector, features)

        window_start = now - timedelta(hours=WINDOW_HOURS)
        anomaly_row = AnomalyResult(
            well_id=well.id,
            calculated_at=now,
            algorithm=anomaly.algorithm,
            anomaly_score=anomaly.anomaly_score,
            is_anomaly=anomaly.is_anomaly,
            window_start=window_start,
            window_end=now,
            features=features,
            details=anomaly.details,
        )
        self.db.add(anomaly_row)
        self.db.flush()

        prediction_row = PredictionResult(
            well_id=well.id,
            calculated_at=now,
            model_name=prediction.model_name,
            model_version=prediction.model_version,
            failure_probability=prediction.failure_probability,
            risk_category=prediction.risk_category,
            horizon_days=prediction.horizon_days,
            top_factors=prediction.top_factors,
            presumed_failure_type=prediction.presumed_failure_type,
            is_reliable=prediction.is_reliable,
            reliability_note=prediction.reliability_note,
            features=features,
        )
        self.db.add(prediction_row)
        self.db.flush()

        alerts_created = 0
        alerts_created += self._maybe_create_threshold_alerts(well, features, now)
        if anomaly.is_anomaly:
            alerts_created += self._create_alert(
                well_id=well.id,
                alert_type=ALERT_TYPE_ANOMALY,
                severity=SEVERITY_WARNING,
                message=(
                    f"Обнаружена аномалия режима работы скважины {well.name}: "
                    f"score={anomaly.anomaly_score:.3f}"
                ),
                dedup_key=f"anomaly:{well.id}:{now.strftime('%Y%m%d%H')}",
                anomaly_id=anomaly_row.id,
            )
        if prediction.risk_category in {RISK_MEDIUM, RISK_HIGH}:
            sev = SEVERITY_CRITICAL if prediction.risk_category == RISK_HIGH else SEVERITY_WARNING
            alerts_created += self._create_alert(
                well_id=well.id,
                alert_type=ALERT_TYPE_FAILURE_RISK,
                severity=sev,
                message=(
                    f"Повышенный риск отказа скважины {well.name}: "
                    f"P={prediction.failure_probability:.2f}, категория={prediction.risk_category}, "
                    f"горизонт={prediction.horizon_days} сут."
                ),
                dedup_key=f"risk:{well.id}:{prediction.risk_category}:{now.strftime('%Y%m%d%H')}",
                prediction_id=prediction_row.id,
            )

        # Update well operational status from analytics
        if prediction.risk_category == RISK_HIGH or well.status == "stopped":
            if well.status not in {"stopped", "maintenance"}:
                well.status = WELL_STATUS_CRITICAL
        elif prediction.risk_category == RISK_MEDIUM or anomaly.is_anomaly:
            if well.status not in {"stopped", "maintenance", WELL_STATUS_CRITICAL}:
                well.status = WELL_STATUS_WARNING
        elif well.status in {WELL_STATUS_WARNING, WELL_STATUS_CRITICAL}:
            well.status = WELL_STATUS_NORMAL

        return {"anomaly": 1, "prediction": 1, "alerts": alerts_created}

    def _maybe_create_threshold_alerts(
        self, well: Well, features: dict[str, float], now: datetime
    ) -> int:
        created = 0
        checks = [
            ("motor_temperature_mean", 110.0, "Температура ПЭД", "°C"),
            ("vibration_mean", 7.0, "Вибрация", "мм/с"),
            ("current_a_mean", 70.0, "Ток фазы A", "А"),
        ]
        for key, limit, title, unit in checks:
            value = features.get(key)
            if value is not None and value >= limit:
                created += self._create_alert(
                    well_id=well.id,
                    alert_type=ALERT_TYPE_THRESHOLD,
                    severity=SEVERITY_CRITICAL if value >= limit * 1.05 else SEVERITY_WARNING,
                    message=f"{title} вне допуска на скважине {well.name}: {value:.1f} {unit} (порог {limit})",
                    dedup_key=f"threshold:{well.id}:{key}:{now.strftime('%Y%m%d%H')}",
                )
        return created

    def _create_alert(
        self,
        *,
        well_id: int,
        alert_type: str,
        severity: str,
        message: str,
        dedup_key: str,
        anomaly_id: int | None = None,
        prediction_id: int | None = None,
    ) -> int:
        existing = (
            self.db.query(Alert)
            .filter(
                Alert.well_id == well_id,
                Alert.alert_type == alert_type,
                Alert.dedup_key == dedup_key,
            )
            .first()
        )
        if existing:
            return 0
        self.db.add(
            Alert(
                well_id=well_id,
                alert_type=alert_type,
                severity=severity,
                message=message,
                status=ALERT_STATUS_NEW,
                anomaly_result_id=anomaly_id,
                prediction_result_id=prediction_id,
                dedup_key=dedup_key,
            )
        )
        return 1

    def _load_telemetry_rows(self, well_id: int, hours: int) -> list[dict[str, Any]]:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        q = (
            self.db.query(Telemetry)
            .filter(
                Telemetry.well_id == well_id,
                Telemetry.recorded_at >= since,
                Telemetry.parameter_code.in_(FEATURE_PARAMS),
                Telemetry.quality_flag != "bad",
            )
            .order_by(Telemetry.recorded_at.asc())
        )
        return [
            {
                "recorded_at": r.recorded_at,
                "parameter_code": r.parameter_code,
                "value": r.value,
            }
            for r in q.all()
        ]

    def _context_counts(self, well_id: int, at: datetime) -> dict[str, float | int]:
        at_aware = at if at.tzinfo else at.replace(tzinfo=timezone.utc)
        since_30 = at_aware - timedelta(days=30)
        failures_30d = (
            self.db.query(Failure)
            .filter(Failure.well_id == well_id, Failure.occurred_at >= since_30)
            .count()
        )
        last_maint = (
            self.db.query(MaintenanceAction)
            .filter(MaintenanceAction.well_id == well_id)
            .order_by(MaintenanceAction.started_at.desc())
            .first()
        )
        if last_maint:
            started = last_maint.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            hours_since = max((at_aware - started).total_seconds() / 3600.0, 0.0)
        else:
            hours_since = 1500.0
        return {
            "failures_30d": failures_30d,
            "hours_since_maintenance": hours_since,
            "operating_hours": 2000.0 + hours_since,
        }

    def _upsert_ml_registry(self, fit_info: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc)
        for purpose, name, algo in [
            ("anomaly", ANOMALY_ALGORITHM, ANOMALY_ALGORITHM),
            ("prediction", PREDICTION_MODEL, PREDICTION_MODEL),
        ]:
            row = (
                self.db.query(MlModel)
                .filter(MlModel.name == name, MlModel.version == ANALYTICS_VERSION)
                .first()
            )
            metrics = fit_info if purpose == "prediction" else {"detector": "IsolationForest"}
            if row:
                row.is_active = True
                row.trained_at = now
                row.metrics = metrics
            else:
                self.db.add(
                    MlModel(
                        name=name,
                        version=ANALYTICS_VERSION,
                        algorithm=algo,
                        purpose=purpose,
                        is_active=True,
                        trained_at=now,
                        metrics=metrics,
                        notes="Синтетические демо-данные; не для промышленной калибровки.",
                    )
                )
