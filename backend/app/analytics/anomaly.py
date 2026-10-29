"""Anomaly detection using Isolation Forest (diploma §2.5 / §3.3)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import IsolationForest

from app.core.config import get_settings
from app.core.constants import ANOMALY_ALGORITHM


@dataclass
class AnomalyAssessment:
    algorithm: str
    anomaly_score: float
    is_anomaly: bool
    details: str


class AnomalyDetector:
    """Isolation Forest wrapper with a transparent rule-based fallback."""

    def __init__(self, contamination: float = 0.12, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.model: IsolationForest | None = None
        self.feature_columns: list[str] = []

    def fit(self, matrix: np.ndarray, feature_columns: list[str]) -> None:
        if matrix.ndim != 2 or matrix.shape[0] < 5:
            self.model = None
            self.feature_columns = feature_columns
            return
        self.feature_columns = feature_columns
        self.model = IsolationForest(
            n_estimators=100,
            contamination=self.contamination,
            random_state=self.random_state,
        )
        self.model.fit(matrix)

    def assess(self, vector: np.ndarray, features: dict[str, float]) -> AnomalyAssessment:
        settings = get_settings()
        rule_score = self._rule_based_score(features)

        if self.model is None or vector.size == 0:
            score = rule_score
            is_anom = score >= settings.anomaly_score_threshold
            return AnomalyAssessment(
                algorithm=f"{ANOMALY_ALGORITHM}+rules_fallback",
                anomaly_score=round(score, 4),
                is_anomaly=is_anom,
                details=(
                    "Isolation Forest не обучен (мало опорных окон); "
                    f"использована экспертная оценка по признакам={score:.3f}"
                ),
            )

        # decision_function: higher = more normal; convert to [0..1] anomaly score
        raw = float(-self.model.decision_function(vector.reshape(1, -1))[0])
        # Normalize roughly via sigmoid-ish map
        if_score = float(1 / (1 + np.exp(-3.0 * raw)))
        # Blend IF with rules for stability on sparse demo data
        score = float(0.7 * if_score + 0.3 * rule_score)
        is_anom = score >= settings.anomaly_score_threshold
        return AnomalyAssessment(
            algorithm=ANOMALY_ALGORITHM,
            anomaly_score=round(score, 4),
            is_anomaly=is_anom,
            details=(
                f"IsolationForest={if_score:.3f}, rules={rule_score:.3f}, "
                f"combined={score:.3f}, threshold={settings.anomaly_score_threshold}"
            ),
        )

    @staticmethod
    def _rule_based_score(features: dict[str, float]) -> float:
        breach = min(features.get("threshold_breaches", 0.0) / 20.0, 1.0)
        unstable = min(features.get("unstable_modes", 0.0) / 5.0, 1.0)
        vib = min(max(features.get("vibration_mean", 0.0) - 3.0, 0.0) / 6.0, 1.0)
        motor_t = min(
            max(features.get("motor_temperature_mean", 0.0) - 90.0, 0.0) / 30.0, 1.0
        )
        current_cv = min(features.get("current_a_cv", 0.0) / 0.3, 1.0)
        return float(
            min(0.35 * breach + 0.2 * unstable + 0.2 * vib + 0.15 * motor_t + 0.1 * current_cv, 1.0)
        )
