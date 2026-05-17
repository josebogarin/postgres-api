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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Default superuser
    FIRST_SUPERUSER_EMAIL: str
    FIRST_SUPERUSER_PASSWORD: str

    # Primary database
    DATABASE_URL: str

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
    def validate_production_settings(self) -> "Settings":
        if self.APP_ENV == "production" and self.SECRET_KEY == "change-me-in-production-use-openssl-rand-hex-32":
            raise ValueError("SECRET_KEY must be changed in production")
        return self


settings = Settings()  # type: ignore[call-arg]
