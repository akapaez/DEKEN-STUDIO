"""Configuración de la API.

Todas las variables usan el prefijo `DEKEN_`. Cualquier variable puede darse también
como fichero con el sufijo `_FILE` (p. ej. `DEKEN_SECRET_KEY_FILE=/run/secrets/key`),
que es la forma recomendada en producción (Docker secrets).
"""

from __future__ import annotations

import json
import os
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ENV_PREFIX = "DEKEN_"


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


def load_file_variables(environ: dict[str, str] | None = None) -> None:
    """Resuelve variables `DEKEN_X_FILE` en `DEKEN_X` (sin pisar valores explícitos)."""
    env = os.environ if environ is None else environ
    for key in list(env):
        if key.startswith(ENV_PREFIX) and key.endswith("_FILE"):
            target = key[: -len("_FILE")]
            if target in env:
                continue
            path = Path(env[key])
            env[target] = path.read_text(encoding="utf-8").strip()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, extra="ignore", case_sensitive=False)

    environment: Environment = Environment.DEVELOPMENT
    log_level: str = "INFO"
    log_json: bool = True

    secret_key: SecretStr = Field(
        description="Clave para HMAC de CSRF. Mínimo 32 caracteres aleatorios."
    )

    database_url: str = "postgresql+asyncpg://deken:deken@localhost:5432/deken"
    database_pool_size: int = 10
    redis_url: str = "redis://localhost:6379/0"

    # Almacenamiento compatible S3.
    s3_endpoint_url: str = "http://localhost:8333"
    """Endpoint que usa la propia API (red interna)."""
    s3_public_endpoint_url: str | None = None
    """Endpoint con el que se firman URLs para el navegador. Por defecto, el interno."""
    s3_worker_endpoint_url: str | None = None
    """Endpoint con el que se firman URLs para los workers. Por defecto, el público."""
    s3_region: str = "us-east-1"
    s3_access_key: SecretStr = SecretStr("")
    s3_secret_key: SecretStr = SecretStr("")
    s3_bucket: str = "deken-studio"
    s3_force_path_style: bool = True

    # Web / cookies.
    allowed_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    cookie_secure: bool | None = None
    """Por defecto: True en producción, False en desarrollo/test."""
    session_idle_minutes: int = Field(default=12 * 60, ge=5)
    session_absolute_hours: int = Field(default=7 * 24, ge=1)

    # Limitación de intentos de login (ventana deslizante fija).
    login_window_seconds: int = 15 * 60
    login_max_per_email: int = 10
    login_max_per_ip: int = 50

    # URLs firmadas.
    download_url_ttl_seconds: int = Field(default=300, ge=30, le=3600)
    upload_url_ttl_seconds: int = Field(default=900, ge=60, le=6 * 3600)
    input_url_ttl_seconds: int = Field(default=6 * 3600, ge=60, le=12 * 3600)

    # Trabajos.
    job_lease_seconds: int = Field(default=120, ge=10, le=3600)
    job_retry_base_seconds: int = Field(default=30, ge=0, le=3600)
    job_reaper_interval_seconds: int = Field(default=15, ge=1, le=600)
    worker_online_seconds: int = Field(default=90, ge=10)
    max_output_bytes: int = Field(default=20 * 1024**3, ge=1024)

    # Verificación de medios en servidor.
    ffprobe_path: str = "ffprobe"
    ffprobe_timeout_seconds: int = Field(default=60, ge=5, le=600)

    # Límite de cuerpo de peticiones JSON (las subidas van directas a S3).
    max_request_body_bytes: int = Field(default=1024 * 1024, ge=1024)

    # IA (Sprint 2). En Sprint 0 solo se informa de si está configurada.
    ai_provider: str | None = None
    ai_api_key: SecretStr | None = None
    ai_model: str | None = None

    @field_validator("secret_key")
    @classmethod
    def _secret_long_enough(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("DEKEN_SECRET_KEY debe tener al menos 32 caracteres")
        return value

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            value = json.loads(value) if value.strip().startswith("[") else value.split(",")
        if isinstance(value, list):
            return [str(v).strip().rstrip("/") for v in value if str(v).strip()]
        return value

    @model_validator(mode="after")
    def _production_checks(self) -> Settings:
        if self.environment is Environment.PRODUCTION:
            if self.cookie_secure is False:
                raise ValueError("En producción las cookies deben ser Secure")
            if any(o.startswith("http://") for o in self.allowed_origins):
                raise ValueError("En producción los orígenes permitidos deben ser HTTPS")
        return self

    @property
    def secure_cookies(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.environment is Environment.PRODUCTION

    @property
    def public_endpoint(self) -> str:
        return self.s3_public_endpoint_url or self.s3_endpoint_url

    @property
    def worker_endpoint(self) -> str:
        return self.s3_worker_endpoint_url or self.public_endpoint

    @property
    def ai_configured(self) -> bool:
        return bool(self.ai_provider and self.ai_api_key and self.ai_api_key.get_secret_value())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_file_variables()
    return Settings()  # valores desde el entorno
