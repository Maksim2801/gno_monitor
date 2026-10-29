"""Feature engineering for telemetry windows."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd

from app.core.constants import (
    FEATURE_LOOKBACK_HOURS,
    PARAM_CURRENT_A,
    PARAM_FLOW_RATE,
    PARAM_INTAKE_PRESSURE,
    PARAM_MOTOR_TEMPERATURE,
    PARAM_RPM,
    PARAM_TEMPERATURE,
    PARAM_VIBRATION,
    SENSOR_PARAM_SPECS,
    WINDOW_HOURS,
)


FEATURE_PARAMS = [
    PARAM_INTAKE_PRESSURE,
    PARAM_TEMPERATURE,
    PARAM_MOTOR_TEMPERATURE,
    PARAM_CURRENT_A,
    PARAM_VIBRATION,
    PARAM_FLOW_RATE,
    PARAM_RPM,
]


def _to_naive_utc(ts: datetime) -> datetime:
    if ts.tzinfo is not None:
        return ts.astimezone(timezone.utc).replace(tzinfo=None)
    return ts


def telemetry_to_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["recorded_at", "parameter_code", "value"])
    df = pd.DataFrame(rows)
    df["recorded_at"] = pd.to_datetime(df["recorded_at"]).dt.tz_localize(None)
    df = df.sort_values("recorded_at")
    df = df.drop_duplicates(subset=["recorded_at", "parameter_code"], keep="last")
    return df


def clean_series(values: pd.Series, code: str) -> pd.Series:
    spec = SENSOR_PARAM_SPECS.get(code, {})
    vmin = spec.get("min")
    vmax = spec.get("max")
    s = pd.to_numeric(values, errors="coerce")
    if vmin is not None:
        s = s.where(s >= vmin * 0.5)
    if vmax is not None:
        s = s.where(s <= vmax * 1.5)
    return s.interpolate(limit_direction="both").ffill().bfill()


def build_feature_vector(
    df: pd.DataFrame,
    *,
    window_end: datetime | None = None,
    failures_count_30d: int = 0,
    hours_since_maintenance: float | None = None,
    operating_hours: float | None = None,
) -> dict[str, float] | None:
    if df.empty:
        return None

    end = _to_naive_utc(window_end or datetime.now(timezone.utc))
    start = end - timedelta(hours=WINDOW_HOURS)
    lookback_start = end - timedelta(hours=FEATURE_LOOKBACK_HOURS)
    window = df[(df["recorded_at"] >= start) & (df["recorded_at"] <= end)]
    history = df[(df["recorded_at"] >= lookback_start) & (df["recorded_at"] <= end)]
    if window.empty:
        return None

    features: dict[str, float] = {}
    threshold_breaches = 0.0
    unstable_modes = 0.0

    for code in FEATURE_PARAMS:
        series = clean_series(window.loc[window["parameter_code"] == code, "value"], code)
        hist = clean_series(history.loc[history["parameter_code"] == code, "value"], code)
        if series.empty or series.isna().all():
            features[f"{code}_mean"] = 0.0
            features[f"{code}_min"] = 0.0
            features[f"{code}_max"] = 0.0
            features[f"{code}_std"] = 0.0
            features[f"{code}_cv"] = 0.0
            features[f"{code}_slope"] = 0.0
            features[f"{code}_breach_rate"] = 0.0
            continue

        mean = float(series.mean())
        std = float(series.std(ddof=0) or 0.0)
        features[f"{code}_mean"] = mean
        features[f"{code}_min"] = float(series.min())
        features[f"{code}_max"] = float(series.max())
        features[f"{code}_std"] = std
        features[f"{code}_cv"] = float(std / mean) if mean else 0.0

        if len(series) >= 2:
            x = np.arange(len(series), dtype=float)
            slope = float(np.polyfit(x, series.to_numpy(dtype=float), 1)[0])
        else:
            slope = 0.0
        features[f"{code}_slope"] = slope

        spec = SENSOR_PARAM_SPECS.get(code, {})
        cmin = spec.get("critical_min")
        cmax = spec.get("critical_max")
        breaches = 0
        if cmin is not None:
            breaches += int((series < cmin).sum())
        if cmax is not None:
            breaches += int((series > cmax).sum())
        breach_rate = breaches / max(len(series), 1)
        features[f"{code}_breach_rate"] = float(breach_rate)
        threshold_breaches += float(breaches)

        if features[f"{code}_cv"] > 0.15 or abs(slope) > (abs(mean) * 0.02 + 1e-6):
            unstable_modes += 1.0

        # Relative change vs longer history mean
        if not hist.empty and not hist.isna().all():
            hmean = float(hist.mean())
            features[f"{code}_rel_change"] = float((mean - hmean) / hmean) if hmean else 0.0
        else:
            features[f"{code}_rel_change"] = 0.0

    # Combined diagnostic ratios
    flow_mean = features.get(f"{PARAM_FLOW_RATE}_mean", 0.0)
    rpm_mean = features.get(f"{PARAM_RPM}_mean", 0.0)
    features["flow_per_rpm"] = float(flow_mean / rpm_mean) if rpm_mean else 0.0
    features["threshold_breaches"] = threshold_breaches
    features["unstable_modes"] = unstable_modes
    features["failures_30d"] = float(failures_count_30d)
    features["hours_since_maintenance"] = float(
        hours_since_maintenance if hours_since_maintenance is not None else 720.0
    )
    features["operating_hours"] = float(operating_hours if operating_hours is not None else 1000.0)
    features["point_count"] = float(len(window))
    return features


def feature_dict_to_vector(features: dict[str, float], columns: list[str] | None = None) -> tuple[np.ndarray, list[str]]:
    cols = columns or sorted(features.keys())
    vec = np.array([float(features.get(c, 0.0)) for c in cols], dtype=float)
    return vec, cols
