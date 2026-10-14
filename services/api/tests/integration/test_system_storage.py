"""S0-03 (salud), S0-09 (almacenamiento y URLs firmadas) y endurecimiento HTTP."""

from __future__ import annotations

import asyncio
import hashlib
import uuid

import httpx
import pytest

from deken_api.config import Settings
from deken_api.context import AppContext
from deken_api.integrations.storage import Audience, build_object_key
from deken_api.services import system as system_service
from deken_api.testing import ApiClient, ClientFactory

pytestmark = pytest.mark.integration


async def test_live_and_ready(client_factory: ClientFactory) -> None:
    client = await client_factory()
    assert (await client.get("/api/v1/health/live")).json()["status"] == "ok"
    ready = await client.get("/api/v1/health/ready")
    assert ready.status_code == 200
    assert ready.json() == {
        "status": "ok",
        "checks": {"database": "ok", "redis": "ok", "storage": "ok"},
    }


async def test_ready_reports_failures(settings: Settings) -> None:
    broken_storage = AppContext.create(
        settings.model_copy(update={"s3_endpoint_url": "http://127.0.0.1:9"})
    )
    try:
        checks = await system_service.readiness(broken_storage)
        assert checks["storage"]["status"] == "error"
        assert system_service.overall_status(checks) == "error"
    finally:
        await broken_storage.close()

    broken_redis = AppContext.create(
        settings.model_copy(update={"redis_url": "redis://127.0.0.1:9/0"})
    )
    try:
        checks = await system_service.readiness(broken_redis)
        assert checks["redis"]["status"] == "error"
        assert checks["database"]["status"] == "ok"
        assert system_service.overall_status(checks) == "degraded"
    finally:
        await broken_redis.close()


async def test_system_status_reports_real_state(admin_client: ApiClient) -> None:
    status = (await admin_client.get("/api/v1/system/status")).json()
    assert status["status"] == "ok"
    assert status["checks"]["database"]["migration"] == "0002"
    assert status["ffprobe"]["available"] is True
    assert status["workers"] == {"active": 0, "online": 0, "online_names": []}
    assert status["ai"] == {"configured": False, "provider": None}
    assert status["remotion"] == {"license_mode": "evaluation", "commercial_renders_enabled": False}


async def test_presigned_upload_and_download(ctx: AppContext) -> None:
    storage = ctx.storage
    key = build_object_key("system_test", uuid.uuid4(), extension="bin")
    put = storage.presign_put(
        key, audience=Audience.WORKER, ttl_seconds=60, content_type="video/mp4"
    )
    payload = b"\x00prueba-sintetica\x01" * 100
    async with httpx.AsyncClient() as http:
        response = await http.put(put.url, content=payload, headers=put.headers)
        assert response.status_code == 200, response.text
        head = await storage.head(key)
        assert head is not None and head.size_bytes == len(payload)
        assert await storage.sha256(key) == hashlib.sha256(payload).hexdigest()

        get = storage.presign_get(
            key, audience=Audience.BROWSER, ttl_seconds=60, download_filename='../../x"y.mp4'
        )
        downloaded = await http.get(get.url)
        assert downloaded.content == payload
        assert 'filename="x_y.mp4"' in downloaded.headers.get("content-disposition", "")

        tampered = get.url.replace(key, key.replace(".bin", ".otro"))
        assert (await http.get(tampered)).status_code in {403, 404}


async def test_presigned_url_expires(ctx: AppContext) -> None:
    storage = ctx.storage
    key = build_object_key("system_test", uuid.uuid4(), extension="bin")
    await storage.put_bytes(key, b"dato", "application/octet-stream")
    url = storage.presign_get(key, audience=Audience.BROWSER, ttl_seconds=1).url
    await asyncio.sleep(2.1)
    async with httpx.AsyncClient() as http:
        assert (await http.get(url)).status_code == 403


async def test_security_headers_and_request_id(client_factory: ClientFactory) -> None:
    client = await client_factory()
    response = await client.get("/api/v1/health/live", headers={"X-Request-ID": "abc12345-test"})
    assert response.headers["x-request-id"] == "abc12345-test"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    bogus = await client.get("/api/v1/health/live", headers={"X-Request-ID": "<script>"})
    assert bogus.headers["x-request-id"] != "<script>"


async def test_body_size_limit(client_factory: ClientFactory, settings: Settings) -> None:
    client = await client_factory()
    big = "x" * (settings.max_request_body_bytes + 10)
    response = await client.post(
        "/api/v1/auth/login",
        content=f'{{"email":"a@b.c","password":"{big}"}}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
