from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "GNO Monitor"
    app_env: str = "development"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 480
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    database_url: str = (
        "postgresql+psycopg2://gno:gno_secure_password@localhost:5432/gno_monitor"
    )

    admin_username: str = "admin"
    admin_password: str = "ChangeMeAdmin123!"
    admin_full_name: str = "Системный администратор"

    analytics_interval_minutes: int = 15
    prediction_horizon_days: int = 7
    risk_threshold_medium: float = 0.35
    risk_threshold_high: float = 0.65
    anomaly_score_threshold: float = 0.55

    seed_on_startup: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
