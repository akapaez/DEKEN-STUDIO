"""S0-10: contrato de trabajos v1 (cola, lease, reintentos, cancelación, verificación)."""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import subprocess
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from sqlalchemy import update

from deken_api.context import AppContext
from deken_api.db.models import Job, StoredObject
from deken_api.services.jobs import JobService, backoff_seconds
from deken_api.services.workers import authenticate_worker
from deken_api.testing import ApiClient, ClientFactory, TestWorker, WorkerFactory
from deken_render.selftest import encode_args
from deken_shared.jobs import CONTRACT_HEADER, FailRequest, Queue, RenderSelftestPayload

pytestmark = pytest.mark.integration

SELFTEST = "system.render_selftest"


async def _create_job(admin: ApiClient, duration_s: float = 1.0) -> dict[str, Any]:
    response = await admin.post("/api/v1/system/selftest", json={"duration_s": duration_s})
    assert response.status_code == 201, response.text
    return dict(response.json())


async def _claim(client: httpx.AsyncClient, worker: TestWorker, wait: int = 0) -> httpx.Response:
    return await client.post(
        "/api/v1/worker/jobs/claim",
        json={"queues": ["render"], "job_types": [SELFTEST], "wait_seconds": wait},
        headers=worker.headers(),
    )


async def _job(admin: ApiClient, job_id: str) -> dict[str, Any]:
    return dict((await admin.get(f"/api/v1/jobs/{job_id}")).json())


@pytest.fixture
async def worker(make_worker: WorkerFactory) -> TestWorker:
    return await make_worker()


@pytest.fixture
def synthetic_mp4(tmp_path: Path) -> Path:
    """MP4 SINTÉTICO de prueba (1 s) generado con los mismos parámetros del autotest."""
    out = tmp_path / "sintetico.mp4"
    payload = RenderSelftestPayload(duration_s=1.0)
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *encode_args(payload, str(out))],
        check=True,
        timeout=120,
    )
    return out


async def _upload_output(
    client: httpx.AsyncClient, worker: TestWorker, job_id: str, data: bytes
) -> dict[str, Any]:
    ticket = await client.post(
        f"/api/v1/worker/jobs/{job_id}/outputs",
        json={"name": "video", "content_type": "video/mp4", "size_bytes": len(data)},
        headers=worker.headers(),
    )
    assert ticket.status_code == 200, ticket.text
    body = dict(ticket.json())
    async with httpx.AsyncClient() as storage:
        put = await storage.put(body["upload_url"], content=data, headers=body["headers"])
        assert put.status_code == 200
    return body


# --- Autenticación del protocolo --------------------------------------------------------------


async def test_worker_auth_and_contract_version(
    client_factory: ClientFactory, worker: TestWorker, admin_client: ApiClient
) -> None:
    client = await client_factory()
    body = {"queues": ["render"], "job_types": [SELFTEST], "wait_seconds": 0}
    assert (await client.post("/api/v1/worker/jobs/claim", json=body)).status_code == 401
    bad = {**worker.headers(), "Authorization": "Bearer dkw_falso"}
    assert (
        await client.post("/api/v1/worker/jobs/claim", json=body, headers=bad)
    ).status_code == 401
    old = {**worker.headers(), CONTRACT_HEADER: "0"}
    response = await client.post("/api/v1/worker/jobs/claim", json=body, headers=old)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "contract_version_unsupported"

    await admin_client.post(f"/api/v1/workers/{worker.id}/revoke")
    assert (await _claim(client, worker)).status_code == 401


async def test_worker_cannot_claim_foreign_queue(
    client_factory: ClientFactory, make_worker: WorkerFactory
) -> None:
    analysis_only = await make_worker([Queue.ANALYSIS])
    client = await client_factory()
    response = await _claim(client, analysis_only)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "queue_not_allowed"


async def test_heartbeat_registers_capabilities(
    client_factory: ClientFactory, worker: TestWorker, admin_client: ApiClient
) -> None:
    client = await client_factory()
    response = await client.post(
        "/api/v1/worker/heartbeat",
        json={
            "hostname": "equipo-deken",
            "platform": "Linux-WSL2",
            "version": "0.1.0",
            "capabilities": {"ffmpeg_version": "6.1.1", "encoders": ["libx264", "aac"]},
        },
        headers=worker.headers(),
    )
    assert response.status_code == 200
    workers = (await admin_client.get("/api/v1/workers")).json()
    assert workers[0]["online"] is True
    assert workers[0]["capabilities"]["encoders"] == ["libx264", "aac"]
    status = (await admin_client.get("/api/v1/system/status")).json()
    assert status["workers"]["online"] == 1


# --- Reparto y lease ------------------------------------------------------------------------


async def test_empty_queue_returns_204(client_factory: ClientFactory, worker: TestWorker) -> None:
    client = await client_factory()
    assert (await _claim(client, worker)).status_code == 204


async def test_long_poll_wakes_up_when_job_is_created(
    client_factory: ClientFactory, worker: TestWorker, admin_client: ApiClient
) -> None:
    client = await client_factory()
    waiting = asyncio.create_task(_claim(client, worker, wait=10))
    await asyncio.sleep(0.5)
    job = await _create_job(admin_client)
    response = await asyncio.wait_for(waiting, timeout=8)
    assert response.status_code == 200
    assert response.json()["id"] == job["id"]


async def test_concurrent_claims_are_exclusive(
    client_factory: ClientFactory, make_worker: WorkerFactory, admin_client: ApiClient
) -> None:
    job = await _create_job(admin_client)
    workers = [await make_worker() for _ in range(6)]
    client = await client_factory()
    responses = await asyncio.gather(*(_claim(client, w) for w in workers))
    winners = [r for r in responses if r.status_code == 200]
    assert len(winners) == 1
    assert all(r.status_code == 204 for r in responses if r.status_code != 200)
    claimed = winners[0].json()
    assert claimed["id"] == job["id"]
    assert claimed["attempt"] == 1
    assert claimed["payload"]["duration_s"] == 1.0
    detail = await _job(admin_client, job["id"])
    assert detail["job"]["status"] == "processing"


async def test_progress_renews_lease_and_other_workers_are_rejected(
    client_factory: ClientFactory,
    make_worker: WorkerFactory,
    admin_client: ApiClient,
    ctx: AppContext,
) -> None:
    owner, intruder = await make_worker(), await make_worker()
    client = await client_factory()
    job = await _create_job(admin_client)
    claimed = (await _claim(client, owner)).json()
    async with ctx.sessionmaker() as db:
        await db.execute(
            update(Job)
            .where(Job.id == uuid.UUID(job["id"]))
            .values(lease_expires_at=datetime.now(UTC) + timedelta(seconds=2))
        )
        await db.commit()
    ack = await client.post(
        f"/api/v1/worker/jobs/{job['id']}/progress",
        json={"progress": 0.5, "message": "Mitad"},
        headers=owner.headers(),
    )
    assert ack.status_code == 200
    renewed = datetime.fromisoformat(ack.json()["lease_expires_at"])
    assert renewed > datetime.fromisoformat(claimed["lease_expires_at"]) - timedelta(seconds=1)
    assert renewed > datetime.now(UTC) + timedelta(seconds=20)
    stolen = await client.post(
        f"/api/v1/worker/jobs/{job['id']}/progress",
        json={"progress": 0.9},
        headers=intruder.headers(),
    )
    assert stolen.status_code == 409
    assert stolen.json()["error"]["code"] == "lease_lost"
    detail = await _job(admin_client, job["id"])
    assert detail["job"]["progress"] == 0.5
    assert any(e["message"] == "Mitad" for e in detail["events"])


async def test_expired_lease_is_requeued_then_failed(
    client_factory: ClientFactory, worker: TestWorker, admin_client: ApiClient, ctx: AppContext
) -> None:
    client = await client_factory()
    job = await _create_job(admin_client)
    job_id = uuid.UUID(job["id"])

    async def expire_and_reap() -> int:
        async with ctx.sessionmaker() as db:
            await db.execute(
                update(Job)
                .where(Job.id == job_id)
                .values(lease_expires_at=datetime.now(UTC) - timedelta(seconds=1))
            )
            await db.commit()
            return await JobService(db, ctx).reap_expired()

    assert (await _claim(client, worker)).status_code == 200
    assert await expire_and_reap() == 1
    detail = await _job(admin_client, job["id"])
    assert detail["job"]["status"] == "queued"
    assert detail["job"]["attempts"] == 1
    assert detail["job"]["error"]["code"] == "lease_expired"
    assert [e["kind"] for e in detail["events"]][-2:] == ["lease_expired", "retry_scheduled"]

    second = await _claim(client, worker)
    assert second.json()["attempt"] == 2
    assert await expire_and_reap() == 1
    detail = await _job(admin_client, job["id"])
    assert detail["job"]["status"] == "failed"
    assert detail["job"]["finished_at"] is not None


async def test_retryable_failure_uses_backoff(
    client_factory: ClientFactory, worker: TestWorker, admin_client: ApiClient, ctx: AppContext
) -> None:
    assert [backoff_seconds(30, a) for a in (1, 2, 3)] == [30, 60, 120]
    assert backoff_seconds(30, 20) == 3600

    client = await client_factory()
    job = await _create_job(admin_client)
    await _claim(client, worker)
    slow_ctx = dataclasses.replace(
        ctx, settings=ctx.settings.model_copy(update={"job_retry_base_seconds": 30})
    )
    async with ctx.sessionmaker() as db:
        db_worker = await authenticate_worker(db, worker.token)
        assert db_worker is not None
        failed = await JobService(db, slow_ctx).fail(
            uuid.UUID(job["id"]),
            db_worker,
            FailRequest(code="ffmpeg_failed", message="fallo transitorio", retryable=True),
        )
        assert failed.status == "queued"
        assert failed.run_after > datetime.now(UTC) + timedelta(seconds=25)
    # Aún no se puede reclamar: está esperando el backoff.
    assert (await _claim(client, worker)).status_code == 204


async def test_non_retryable_failure_and_manual_retry(
    client_factory: ClientFactory, worker: TestWorker, admin_client: ApiClient
) -> None:
    client = await client_factory()
    job = await _create_job(admin_client)
    await _claim(client, worker)
    response = await client.post(
        f"/api/v1/worker/jobs/{job['id']}/fail",
        json={"code": "invalid_payload", "message": "no válido", "retryable": False},
        headers=worker.headers(),
    )
    assert response.json()["status"] == "failed"
    detail = await _job(admin_client, job["id"])
    assert detail["job"]["error"]["code"] == "invalid_payload"

    retried = await admin_client.post(f"/api/v1/jobs/{job['id']}/retry")
    assert retried.status_code == 200
    assert retried.json()["status"] == "queued"
    assert retried.json()["attempts"] == 0
    assert (await _claim(client, worker)).json()["attempt"] == 1


# --- Cancelación --------------------------------------------------------------------------


async def test_cancel_queued_and_processing(
    client_factory: ClientFactory, worker: TestWorker, admin_client: ApiClient
) -> None:
    client = await client_factory()
    queued = await _create_job(admin_client)
    cancelled = await admin_client.post(f"/api/v1/jobs/{queued['id']}/cancel")
    assert cancelled.json()["status"] == "cancelled"
    again = await admin_client.post(f"/api/v1/jobs/{queued['id']}/cancel")
    assert again.status_code == 409

    running = await _create_job(admin_client)
    await _claim(client, worker)
    requested = await admin_client.post(f"/api/v1/jobs/{running['id']}/cancel")
    assert requested.json()["status"] == "processing"
    assert requested.json()["cancel_requested"] is True
    ack = await client.post(
        f"/api/v1/worker/jobs/{running['id']}/progress",
        json={"progress": 0.3},
        headers=worker.headers(),
    )
    assert ack.json()["cancel_requested"] is True
    done = await client.post(
        f"/api/v1/worker/jobs/{running['id']}/cancelled", headers=worker.headers()
    )
    assert done.json()["status"] == "cancelled"


# --- Salidas y verificación ---------------------------------------------------------------------


async def test_unexpected_outputs_are_rejected(
    client_factory: ClientFactory, worker: TestWorker, admin_client: ApiClient
) -> None:
    client = await client_factory()
    job = await _create_job(admin_client)
    await _claim(client, worker)
    for body in (
        {"name": "otra", "content_type": "video/mp4", "size_bytes": 10},
        {"name": "video", "content_type": "image/png", "size_bytes": 10},
        {"name": "video", "content_type": "text/html", "size_bytes": 10},
        {"name": "../video", "content_type": "video/mp4", "size_bytes": 10},
    ):
        response = await client.post(
            f"/api/v1/worker/jobs/{job['id']}/outputs", json=body, headers=worker.headers()
        )
        assert response.status_code == 422, body


async def test_complete_without_outputs_fails(
    client_factory: ClientFactory, worker: TestWorker, admin_client: ApiClient
) -> None:
    client = await client_factory()
    job = await _create_job(admin_client)
    await _claim(client, worker)
    response = await client.post(
        f"/api/v1/worker/jobs/{job['id']}/complete",
        json={"outputs": [], "result": {}},
        headers=worker.headers(),
    )
    assert response.json()["status"] == "failed"
    detail = await _job(admin_client, job["id"])
    assert detail["job"]["error"]["code"] == "missing_output"


@pytest.mark.parametrize("defect", ["not_a_video", "wrong_sha256", "wrong_size"])
async def test_invalid_outputs_fail_verification(
    defect: str,
    client_factory: ClientFactory,
    worker: TestWorker,
    admin_client: ApiClient,
    ctx: AppContext,
    synthetic_mp4: Path,
) -> None:
    client = await client_factory()
    job = await _create_job(admin_client)
    await _claim(client, worker)
    data = b"esto no es un video" * 50 if defect == "not_a_video" else synthetic_mp4.read_bytes()
    ticket = await _upload_output(client, worker, job["id"], data)
    sha = hashlib.sha256(data).hexdigest()
    size = len(data)
    if defect == "wrong_sha256":
        sha = "0" * 64
    if defect == "wrong_size":
        size += 1
    response = await client.post(
        f"/api/v1/worker/jobs/{job['id']}/complete",
        json={
            "outputs": [
                {
                    "name": "video",
                    "object_id": ticket["object_id"],
                    "sha256": sha,
                    "size_bytes": size,
                }
            ]
        },
        headers=worker.headers(),
    )
    assert response.json()["status"] == "failed"
    detail = await _job(admin_client, job["id"])
    assert detail["job"]["error"]["code"] == "output_verification_failed"
    assert detail["outputs"][0]["verified"] is False
    async with ctx.sessionmaker() as db:
        obj = await db.get(StoredObject, uuid.UUID(ticket["object_id"]))
        assert obj is not None and obj.status == "rejected"
    download = await admin_client.get(f"/api/v1/files/{ticket['object_id']}/download-url")
    assert download.status_code == 409


async def test_wrong_spec_video_fails_verification(
    client_factory: ClientFactory, worker: TestWorker, admin_client: ApiClient, tmp_path: Path
) -> None:
    """Un vídeo válido pero horizontal (16:9) no cumple la especificación 1080×1920."""
    client = await client_factory()
    job = await _create_job(admin_client)
    await _claim(client, worker)
    wrong = tmp_path / "horizontal.mp4"
    payload = RenderSelftestPayload(duration_s=1.0, width=1920, height=1080)
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *encode_args(payload, str(wrong))],
        check=True,
        timeout=120,
    )
    data = wrong.read_bytes()
    ticket = await _upload_output(client, worker, job["id"], data)
    await client.post(
        f"/api/v1/worker/jobs/{job['id']}/complete",
        json={
            "outputs": [
                {
                    "name": "video",
                    "object_id": ticket["object_id"],
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "size_bytes": len(data),
                }
            ]
        },
        headers=worker.headers(),
    )
    detail = await _job(admin_client, job["id"])
    assert detail["job"]["status"] == "failed"
    problems = detail["job"]["error"]["details"]["video"]
    assert any("resolución 1920x1080" in p for p in problems)


async def test_valid_output_completes_and_is_downloadable(
    client_factory: ClientFactory,
    worker: TestWorker,
    admin_client: ApiClient,
    synthetic_mp4: Path,
) -> None:
    client = await client_factory()
    job = await _create_job(admin_client, duration_s=1.0)
    await _claim(client, worker)
    data = synthetic_mp4.read_bytes()
    ticket = await _upload_output(client, worker, job["id"], data)
    response = await client.post(
        f"/api/v1/worker/jobs/{job['id']}/complete",
        json={
            "outputs": [
                {
                    "name": "video",
                    "object_id": ticket["object_id"],
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "size_bytes": len(data),
                }
            ],
            "result": {"synthetic": True},
        },
        headers=worker.headers(),
    )
    assert response.json()["status"] == "completed"
    detail = await _job(admin_client, job["id"])
    assert detail["job"]["result"]["outputs"]["video"] == ticket["object_id"]
    output = detail["outputs"][0]
    assert output["verified"] is True
    info = output["stored_object"]["media_info"]
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    assert (video["width"], video["height"], video["codec_name"]) == (1080, 1920, "h264")

    link = await admin_client.get(f"/api/v1/files/{ticket['object_id']}/download-url")
    assert link.status_code == 200
    assert link.json()["filename"].startswith("deken-autotest-sintetico-")
    async with httpx.AsyncClient() as storage:
        downloaded = await storage.get(link.json()["url"])
    assert hashlib.sha256(downloaded.content).hexdigest() == hashlib.sha256(data).hexdigest()

    # Una vez completado, el worker ya no puede volver a tocar el trabajo.
    late = await client.post(
        f"/api/v1/worker/jobs/{job['id']}/progress", json={"progress": 1}, headers=worker.headers()
    )
    assert late.status_code == 409
