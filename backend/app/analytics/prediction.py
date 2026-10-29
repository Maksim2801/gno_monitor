"""Failure risk prediction: Random Forest + documented expert fallback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from app.core.config import get_settings
from app.core.constants import (
    ANALYTICS_VERSION,
    MIN_LABELED_SAMPLES_FOR_RF,
    PREDICTION_MODEL,
    risk_category,
)


@dataclass
class PredictionAssessment:
    model_name: str
    model_version: str
    failure_probability: float
    risk_category: str
    horizon_days: int
    top_factors: list[dict[str, Any]]
    presumed_failure_type: str | None
    is_reliable: bool
    reliability_note: str


class FailureRiskPredictor:
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.model: RandomForestClassifier | None = None
        self.feature_columns: list[str] = []
        self.trained_samples = 0

    def fit(self, matrix: np.ndarray, labels: np.ndarray, feature_columns: list[str]) -> dict[str, Any]:
        self.feature_columns = feature_columns
        self.trained_samples = int(matrix.shape[0]) if matrix.ndim == 2 else 0
        if (
            matrix.ndim != 2
            or matrix.shape[0] < MIN_LABELED_SAMPLES_FOR_RF
            or len(np.unique(labels)) < 2
        ):
            self.model = None
            return {
                "trained": False,
                "samples": self.trained_samples,
                "reason": "Недостаточно размеченных окон для обучения Random Forest",
            }

        self.model = RandomForestClassifier(
            n_estimators=120,
            max_depth=8,
            min_samples_leaf=2,
            random_state=self.random_state,
            class_weight="balanced",
        )
        self.model.fit(matrix, labels)
        train_acc = float(self.model.score(matrix, labels))
        return {
            "trained": True,
            "samples": self.trained_samples,
            "train_accuracy": round(train_acc, 4),
            "note": (
                "Точность на обучающей выборке не является внешней валидацией; "
                "для демо используется синтетическая разметка по истории отказов."
            ),
        }

    def predict(self, vector: np.ndarray, features: dict[str, float]) -> PredictionAssessment:
        settings = get_settings()
        horizon = settings.prediction_horizon_days
        expert_prob, expert_factors, presumed = self._expert_probability(features)

        if self.model is None:
            category = risk_category(expert_prob)
            return PredictionAssessment(
                model_name=f"{PREDICTION_MODEL}_expert_fallback",
                model_version=ANALYTICS_VERSION,
                failure_probability=round(expert_prob, 4),
                risk_category=category,
                horizon_days=horizon,
                top_factors=expert_factors,
                presumed_failure_type=presumed,
                is_reliable=False,
                reliability_note=(
                    "Достоверный прогноз RF недоступен: мало размеченной истории отказов. "
                    "Показана экспертно-статистическая оценка риска (не калиброванная вероятность)."
                ),
            )

        proba = float(self.model.predict_proba(vector.reshape(1, -1))[0][1])
        # Blend with expert score to reduce overconfidence on synthetic labels
        blended = float(0.65 * proba + 0.35 * expert_prob)
        importances = getattr(self.model, "feature_importances_", None)
        top_factors: list[dict[str, Any]] = []
        if importances is not None and self.feature_columns:
            ranked = sorted(
                zip(self.feature_columns, importances, strict=False),
                key=lambda x: x[1],
                reverse=True,
            )[:5]
            for name, imp in ranked:
                top_factors.append(
                    {
                        "factor": name,
                        "importance": round(float(imp), 4),
                        "value": round(float(features.get(name, 0.0)), 4),
                    }
                )
        else:
            top_factors = expert_factors

        return PredictionAssessment(
            model_name=PREDICTION_MODEL,
            model_version=ANALYTICS_VERSION,
            failure_probability=round(blended, 4),
            risk_category=risk_category(blended),
            horizon_days=horizon,
            top_factors=top_factors,
            presumed_failure_type=presumed,
            is_reliable=True,
            reliability_note=(
                f"Оценка RF на горизонте {horizon} сут. по синтетически размеченным окнам "
                f"(n={self.trained_samples}). Не является промышленно калиброванной вероятностью."
            ),
        )

    @staticmethod
    def _expert_probability(
        features: dict[str, float],
    ) -> tuple[float, list[dict[str, Any]], str | None]:
        factors: list[tuple[str, float, float]] = []
        # (name, contribution weight, normalized severity 0..1)
        vib = min(max(features.get("vibration_mean", 0.0) - 3.5, 0.0) / 5.0, 1.0)
        factors.append(("vibration_mean", 0.18, vib))
        motor = min(max(features.get("motor_temperature_mean", 0.0) - 95.0, 0.0) / 25.0, 1.0)
        factors.append(("motor_temperature_mean", 0.16, motor))
        pressure_drop = min(
            max(4.0 - features.get("intake_pressure_mean", 4.0), 0.0) / 3.0, 1.0
        )
        factors.append(("intake_pressure_mean", 0.12, pressure_drop))
        current_cv = min(features.get("current_a_cv", 0.0) / 0.25, 1.0)
        factors.append(("current_a_cv", 0.12, current_cv))
        flow_rpm = features.get("flow_per_rpm", 0.0)
        flow_deg = min(max(0.08 - flow_rpm, 0.0) / 0.08, 1.0) if flow_rpm else 0.4
        factors.append(("flow_per_rpm", 0.12, flow_deg))
        breaches = min(features.get("threshold_breaches", 0.0) / 15.0, 1.0)
        factors.append(("threshold_breaches", 0.12, breaches))
        fails = min(features.get("failures_30d", 0.0) / 3.0, 1.0)
        factors.append(("failures_30d", 0.1, fails))
        maint = min(features.get("hours_since_maintenance", 720.0) / 2000.0, 1.0)
        factors.append(("hours_since_maintenance", 0.08, maint))

        prob = float(min(sum(w * s for _, w, s in factors), 0.99))
        top = sorted(factors, key=lambda x: x[1] * x[2], reverse=True)[:5]
        top_factors = [
            {
                "factor": name,
                "importance": round(w * s, 4),
                "value": round(float(features.get(name, s)), 4),
            }
            for name, w, s in top
        ]

        presumed = None
        if motor >= 0.6:
            presumed = "Перегрев ПЭД"
        elif vib >= 0.6:
            presumed = "Механический износ / вибрация"
        elif pressure_drop >= 0.6:
            presumed = "Срыв подачи / снижение давления на приёме"
        elif current_cv >= 0.6:
            presumed = "Нестабильная токовая нагрузка"
        return prob, top_factors, presumed
