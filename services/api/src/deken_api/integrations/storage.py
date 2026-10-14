"""Almacenamiento de objetos compatible S3.

- La API usa el endpoint interno para operar y firma URLs con el endpoint que
  corresponda a quién las va a usar (navegador o worker).
- Las claves se construyen aquí, siempre a partir de UUID generados por el servidor.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Any

import anyio
import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = Any

KIND_PREFIXES = {
    "original": "originals",
    "derived": "derived",
    "render": "renders",
    "brand": "brand",
    "system_test": "system",
}

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._ -]+")


class Audience(StrEnum):
    INTERNAL = "internal"
    BROWSER = "browser"
    WORKER = "worker"


class StorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class ObjectHead:
    size_bytes: int
    content_type: str | None
    etag: str | None


@dataclass(frozen=True)
class PresignedUrl:
    url: str
    expires_at: datetime
    headers: dict[str, str]


def build_object_key(kind: str, *parts: uuid.UUID | int, extension: str) -> str:
    """Clave del objeto: `<prefijo>/<uuid>/.../<uuid>.<ext>`. Nunca contiene entrada de usuario."""
    if kind not in KIND_PREFIXES:
        raise ValueError(f"tipo de objeto desconocido: {kind}")
    if not re.fullmatch(r"[a-z0-9]{1,8}", extension):
        raise ValueError("extensión no válida")
    segments = [KIND_PREFIXES[kind], *(str(p) for p in parts), f"{uuid.uuid4()}.{extension}"]
    return "/".join(segments)


def safe_download_filename(name: str, fallback: str = "archivo") -> str:
    """Nombre para Content-Disposition: sin rutas, comillas ni caracteres de control."""
    base = name.replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = _SAFE_FILENAME.sub("_", base).strip(" .")
    return cleaned[:150] or fallback


class ObjectStorage:
    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        access_key: str,
        secret_key: str,
        endpoints: dict[Audience, str],
        force_path_style: bool = True,
    ) -> None:
        self.bucket = bucket
        self._clients: dict[str, S3Client] = {}
        self._endpoints = endpoints
        self._region = region
        self._access_key = access_key
        self._secret_key = secret_key
        self._force_path_style = force_path_style

    def _make(self, endpoint: str) -> S3Client:
        client: S3Client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=self._region,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path" if self._force_path_style else "auto"},
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=5,
                read_timeout=60,
            ),
        )
        return client

    def _client(self, audience: Audience) -> S3Client:
        endpoint = self._endpoints[audience]
        if endpoint not in self._clients:
            self._clients[endpoint] = self._make(endpoint)
        return self._clients[endpoint]

    @property
    def internal(self) -> S3Client:
        return self._client(Audience.INTERNAL)

    # --- Operaciones (bloqueantes, se ejecutan en hilo) --------------------------------

    def _ensure_bucket_sync(self) -> bool:
        try:
            self.internal.head_bucket(Bucket=self.bucket)
            return False
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code not in {"404", "NoSuchBucket", "NotFound"}:
                raise StorageError(f"no se puede acceder al bucket: {exc}") from exc
        self.internal.create_bucket(Bucket=self.bucket)
        return True

    async def ensure_bucket(self) -> bool:
        """Crea el bucket si no existe. Devuelve True si lo ha creado."""
        return await anyio.to_thread.run_sync(self._ensure_bucket_sync)

    def _head_sync(self, key: str) -> ObjectHead | None:
        try:
            resp = self.internal.head_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise StorageError(str(exc)) from exc
        return ObjectHead(
            size_bytes=int(resp["ContentLength"]),
            content_type=resp.get("ContentType"),
            etag=resp.get("ETag"),
        )

    async def head(self, key: str) -> ObjectHead | None:
        return await anyio.to_thread.run_sync(self._head_sync, key)

    def _sha256_sync(self, key: str) -> str:
        body = self.internal.get_object(Bucket=self.bucket, Key=key)["Body"]
        digest = hashlib.sha256()
        for chunk in body.iter_chunks(chunk_size=1024 * 1024):
            digest.update(chunk)
        return digest.hexdigest()

    async def sha256(self, key: str) -> str:
        return await anyio.to_thread.run_sync(self._sha256_sync, key)

    async def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        def _put() -> None:
            self.internal.put_object(
                Bucket=self.bucket, Key=key, Body=data, ContentType=content_type
            )

        await anyio.to_thread.run_sync(_put)

    async def delete(self, key: str) -> None:
        await anyio.to_thread.run_sync(
            lambda: self.internal.delete_object(Bucket=self.bucket, Key=key)
        )

    async def health(self) -> None:
        def _check() -> None:
            try:
                self.internal.head_bucket(Bucket=self.bucket)
            except (ClientError, BotoCoreError) as exc:
                raise StorageError(str(exc)) from exc

        await anyio.to_thread.run_sync(_check)

    # --- URLs firmadas (cálculo local, sin E/S) -----------------------------------------

    def presign_get(
        self,
        key: str,
        *,
        audience: Audience,
        ttl_seconds: int,
        download_filename: str | None = None,
    ) -> PresignedUrl:
        params: dict[str, Any] = {"Bucket": self.bucket, "Key": key}
        if download_filename:
            params["ResponseContentDisposition"] = (
                f'attachment; filename="{safe_download_filename(download_filename)}"'
            )
        url = self._client(audience).generate_presigned_url(
            "get_object", Params=params, ExpiresIn=ttl_seconds
        )
        return PresignedUrl(url=url, expires_at=_expiry(ttl_seconds), headers={})

    def presign_put(
        self, key: str, *, audience: Audience, ttl_seconds: int, content_type: str
    ) -> PresignedUrl:
        url = self._client(audience).generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=ttl_seconds,
        )
        return PresignedUrl(
            url=url, expires_at=_expiry(ttl_seconds), headers={"Content-Type": content_type}
        )


def _expiry(ttl_seconds: int) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=ttl_seconds)
