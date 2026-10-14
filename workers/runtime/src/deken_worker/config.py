"""Configuración del worker (variables `DEKEN_*`)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DEKEN_", extra="ignore")

    api_url: str = Field(description="URL base de la API, p. ej. https://studio.deken.es")
    worker_token: SecretStr = Field(description="Token emitido en Configuración → Workers")
    worker_queues: Annotated[list[str], NoDecode] = ["render", "analysis"]
    work_dir: Path = Path(tempfile.gettempdir()) / "deken-worker"
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    claim_wait_seconds: int = Field(default=20, ge=0, le=30)
    heartbeat_seconds: int = Field(default=30, ge=5, le=300)
    progress_min_interval_seconds: float = Field(default=2.0, ge=0.2, le=60)
    http_timeout_seconds: float = Field(default=60.0, ge=5, le=600)
    ca_bundle: str | None = None
    """Ruta a un bundle de CA propio (p. ej. proxy corporativo). Por defecto, el del sistema."""

    @field_validator("api_url")
    @classmethod
    def _strip_slash(cls, value: str) -> str:
        value = value.rstrip("/")
        if not value.startswith(("http://", "https://")):
            raise ValueError("DEKEN_API_URL debe empezar por http:// o https://")
        return value

    @field_validator("worker_queues", mode="before")
    @classmethod
    def _split(cls, value: object) -> object:
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value
