import json
from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    APP_NAME: str = "Postgres API"
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 horas
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Default superuser
    FIRST_SUPERUSER_EMAIL: str
    FIRST_SUPERUSER_PASSWORD: str

    # Primary database
    DATABASE_URL: str

    # BECBUC
    DATABASE_BECBUC_URL: str = ""

    # API-Football
    APIFOOTBALL_KEY: str = ""

    # Monitor de partidos
    MONITOR_ACTIVO: bool = True
    MONITOR_LEAGUE_ID: int = 1
    MONITOR_SEASON: int = 2026
    MONITOR_STARTUP_MARGIN_SEG: int = 300
    MONITOR_INTERVAL_FAR_SEG: int = 600
    MONITOR_INTERVAL_NEAR_SEG: int = 150
    MONITOR_INTERVAL_IMMIN_SEG: int = 45
    MONITOR_INTERVAL_LIVE_SEG: int = 45
    MONITOR_INTERVAL_HT_SEG: int = 90
    MONITOR_GRACE_PERIOD_SEG: int = 600
    MONITOR_MAX_CALLS_DIA: int = 80

    # Additional databases per application {"app_slug": "connection_url"}
    APP_DATABASES: dict[str, str] = {}

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = []

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    @field_validator("APP_DATABASES", mode="before")
    @classmethod
    def parse_app_databases(cls, v: Any) -> dict:
        if isinstance(v, str):
            return json.loads(v)
        return v or {}

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v: Any) -> list:
        if isinstance(v, str):
            return json.loads(v)
        return v or []

    @model_validator(mode="after")
    def apply_settings_rules(self) -> "Settings":
        # En desarrollo, permitir origen "null" (archivos HTML abiertos desde file://)
        if self.APP_ENV == "development" and "null" not in self.BACKEND_CORS_ORIGINS:
            self.BACKEND_CORS_ORIGINS = list(self.BACKEND_CORS_ORIGINS) + ["null"]

        # En producciÃ³n, la SECRET_KEY debe estar cambiada
        if self.APP_ENV == "production" and self.SECRET_KEY == "change-me-in-production-use-openssl-rand-hex-32":
            raise ValueError("SECRET_KEY must be changed in production")

        return self


settings = Settings()  # type: ignore[call-arg]

