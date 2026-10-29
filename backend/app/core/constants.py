"""Centralized thresholds and domain constants (no magic numbers in business logic)."""

from app.core.config import get_settings


# Sensor parameter codes used across telemetry, analytics and UI
PARAM_INTAKE_PRESSURE = "intake_pressure"
PARAM_TEMPERATURE = "temperature"
PARAM_MOTOR_TEMPERATURE = "motor_temperature"
PARAM_CURRENT_A = "current_a"
PARAM_CURRENT_B = "current_b"
PARAM_CURRENT_C = "current_c"
PARAM_VOLTAGE_A = "voltage_a"
PARAM_VOLTAGE_B = "voltage_b"
PARAM_VOLTAGE_C = "voltage_c"
PARAM_FREQUENCY = "frequency"
PARAM_POWER = "power"
PARAM_LOAD = "load"
PARAM_VIBRATION = "vibration"
PARAM_FLOW_RATE = "flow_rate"
PARAM_RPM = "rpm"

SENSOR_PARAM_SPECS: dict[str, dict] = {
    PARAM_INTAKE_PRESSURE: {
        "name": "Давление на приёме насоса",
        "unit": "МПа",
        "min": 0.5,
        "max": 12.0,
        "critical_min": 1.0,
        "critical_max": 10.0,
    },
    PARAM_TEMPERATURE: {
        "name": "Температура",
        "unit": "°C",
        "min": 20.0,
        "max": 120.0,
        "critical_min": 30.0,
        "critical_max": 105.0,
    },
    PARAM_MOTOR_TEMPERATURE: {
        "name": "Температура электродвигателя",
        "unit": "°C",
        "min": 20.0,
        "max": 130.0,
        "critical_min": 35.0,
        "critical_max": 115.0,
    },
    PARAM_CURRENT_A: {
        "name": "Ток фазы A",
        "unit": "А",
        "min": 10.0,
        "max": 80.0,
        "critical_min": 15.0,
        "critical_max": 70.0,
    },
    PARAM_CURRENT_B: {
        "name": "Ток фазы B",
        "unit": "А",
        "min": 10.0,
        "max": 80.0,
        "critical_min": 15.0,
        "critical_max": 70.0,
    },
    PARAM_CURRENT_C: {
        "name": "Ток фазы C",
        "unit": "А",
        "min": 10.0,
        "max": 80.0,
        "critical_min": 15.0,
        "critical_max": 70.0,
    },
    PARAM_VOLTAGE_A: {
        "name": "Напряжение фазы A",
        "unit": "В",
        "min": 300.0,
        "max": 450.0,
        "critical_min": 340.0,
        "critical_max": 420.0,
    },
    PARAM_VOLTAGE_B: {
        "name": "Напряжение фазы B",
        "unit": "В",
        "min": 300.0,
        "max": 450.0,
        "critical_min": 340.0,
        "critical_max": 420.0,
    },
    PARAM_VOLTAGE_C: {
        "name": "Напряжение фазы C",
        "unit": "В",
        "min": 300.0,
        "max": 450.0,
        "critical_min": 340.0,
        "critical_max": 420.0,
    },
    PARAM_FREQUENCY: {
        "name": "Частота",
        "unit": "Гц",
        "min": 30.0,
        "max": 60.0,
        "critical_min": 35.0,
        "critical_max": 55.0,
    },
    PARAM_POWER: {
        "name": "Мощность",
        "unit": "кВт",
        "min": 20.0,
        "max": 200.0,
        "critical_min": 30.0,
        "critical_max": 180.0,
    },
    PARAM_LOAD: {
        "name": "Загрузка",
        "unit": "%",
        "min": 20.0,
        "max": 110.0,
        "critical_min": 30.0,
        "critical_max": 100.0,
    },
    PARAM_VIBRATION: {
        "name": "Вибрация",
        "unit": "мм/с",
        "min": 0.0,
        "max": 12.0,
        "critical_min": 0.0,
        "critical_max": 7.0,
    },
    PARAM_FLOW_RATE: {
        "name": "Дебит жидкости",
        "unit": "м³/сут",
        "min": 10.0,
        "max": 400.0,
        "critical_min": 20.0,
        "critical_max": 350.0,
    },
    PARAM_RPM: {
        "name": "Частота вращения",
        "unit": "об/мин",
        "min": 1500.0,
        "max": 3500.0,
        "critical_min": 1800.0,
        "critical_max": 3200.0,
    },
}

WINDOW_HOURS = 6
FEATURE_LOOKBACK_HOURS = 72
MIN_POINTS_FOR_ANALYTICS = 12
MIN_LABELED_SAMPLES_FOR_RF = 20

ANOMALY_ALGORITHM = "IsolationForest"
PREDICTION_MODEL = "RandomForestClassifier"
ANALYTICS_VERSION = "1.0.0"

ALERT_TYPE_THRESHOLD = "threshold"
ALERT_TYPE_ANOMALY = "anomaly"
ALERT_TYPE_FAILURE_RISK = "failure_risk"
ALERT_TYPE_INFO = "info"

SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"

ALERT_STATUS_NEW = "new"
ALERT_STATUS_ACKNOWLEDGED = "acknowledged"
ALERT_STATUS_CLOSED = "closed"

RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"

WELL_STATUS_NORMAL = "normal"
WELL_STATUS_WARNING = "warning"
WELL_STATUS_CRITICAL = "critical"
WELL_STATUS_STOPPED = "stopped"
WELL_STATUS_MAINTENANCE = "maintenance"


def risk_category(probability: float) -> str:
    settings = get_settings()
    if probability >= settings.risk_threshold_high:
        return RISK_HIGH
    if probability >= settings.risk_threshold_medium:
        return RISK_MEDIUM
    return RISK_LOW
