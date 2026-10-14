"""Cliente HTTP y runtime del worker con un transporte simulado de la API.

Estos tests NO sustituyen a los de integración (services/api/tests/integration): solo
comprueban la lógica del cliente (reintentos, mapeo de errores, cabeceras) de forma
determinista.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest

from deken_shared.jobs import (
    CONTRACT_HEADER,
    ClaimedJob,
    ClaimRequest,
    OutputUploadTicket,
    ProgressReport,
    Queue,
)
from deken_worker.client import ApiClientError, LeaseLostError, WorkerClient
from deken_worker.config import WorkerSettings
from deken_worker.process import ProcessFailedError
from deken_worker.runtime import HandlerResult, JobContext, JobError, Worker

TOKEN = "dkw_token-de-prueba"


def _client(handler: Any, **kw: Any) -> WorkerClient:
    return WorkerClient(
        "http://api.test", TOKEN, transport=httpx.MockTransport(handler), sleep=lambda _: None, **kw
    )


def test_requests_carry_token_and_contract_header() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(204)

    client = _client(handler)
    assert (
        client.claim(ClaimRequest(queues=[Queue.RENDER], job_types=["x"], wait_seconds=0)) is None
    )
    assert seen[0].headers["authorization"] == f"Bearer {TOKEN}"
    assert seen[0].headers[CONTRACT_HEADER] == "1"
    assert seen[0].url.path == "/api/v1/worker/jobs/claim"


def test_retries_transient_errors_then_succeeds() -> None:
    calls = {"n": 0}
    lease = (datetime.now(UTC) + timedelta(minutes=1)).isoformat()

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"cancel_requested": False, "lease_expires_at": lease})

    ack = _client(handler).progress(uuid.uuid4(), ProgressReport(progress=0.5))
    assert calls["n"] == 3
    assert ack.cancel_requested is False


def test_gives_up_after_retries() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin red")

    with pytest.raises(httpx.ConnectError):
        _client(handler, retries=2).progress(uuid.uuid4(), ProgressReport(progress=0.1))


def test_error_mapping() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            409, json={"error": {"code": "lease_lost", "message": "ya no es tuyo"}}
        )

    with pytest.raises(LeaseLostError) as exc:
        _client(handler).progress(uuid.uuid4(), ProgressReport(progress=0.1))
    assert exc.value.status == 409

    def handler2(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"code": "not_authenticated", "message": "no"}})

    with pytest.raises(ApiClientError) as exc2:
        _client(handler2).progress(uuid.uuid4(), ProgressReport(progress=0.1))
    assert exc2.value.code == "not_authenticated"


def test_upload_never_sends_worker_token(tmp_path: Path) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        request.read()
        return httpx.Response(200)

    file = tmp_path / "salida.mp4"
    file.write_bytes(b"0123456789" * 1000)
    ticket = OutputUploadTicket(
        object_id=uuid.uuid4(),
        upload_url="http://storage.test/bucket/key?X-Amz-Signature=abc",
        headers={"Content-Type": "video/mp4"},
        expires_at=datetime.now(UTC),
    )
    _client(handler).upload(ticket, file)
    request = seen[0]
    assert "authorization" not in request.headers
    assert request.headers["content-type"] == "video/mp4"
    assert request.headers["content-length"] == "10000"
    assert request.content == file.read_bytes()


# --- Runtime: mapeo de errores de handlers a llamadas del protocolo ------------------------


class RecordingApi:
    """Transporte que emula las respuestas mínimas de la API y registra las llamadas."""

    def __init__(self, *, cancel: bool = False) -> None:
        self.calls: list[tuple[str, dict[str, Any] | None]] = []
        self.cancel = cancel

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        path = request.url.path.removeprefix("/api/v1")
        self.calls.append((path, body))
        lease = (datetime.now(UTC) + timedelta(minutes=1)).isoformat()
        if path.endswith("/progress"):
            return httpx.Response(
                200, json={"cancel_requested": self.cancel, "lease_expires_at": lease}
            )
        job_id = path.split("/")[3]
        if path.endswith("/fail"):
            return httpx.Response(200, json={"id": job_id, "status": "failed"})
        if path.endswith("/complete"):
            return httpx.Response(200, json={"id": job_id, "status": "completed"})
        if path.endswith("/cancelled"):
            return httpx.Response(200, json={"id": job_id, "status": "cancelled"})
        return httpx.Response(404)

    def paths(self) -> list[str]:
        return [p.rsplit("/", 1)[-1] for p, _ in self.calls]

    def body(self, suffix: str) -> dict[str, Any]:
        return next(b for p, b in self.calls if p.endswith(suffix) and b is not None)


def _job() -> ClaimedJob:
    return ClaimedJob(
        id=uuid.uuid4(),
        type="test.job",
        queue="render",
        attempt=1,
        max_attempts=3,
        payload={},
        inputs=[],
        lease_seconds=60,
        lease_expires_at=datetime.now(UTC) + timedelta(minutes=1),
        timeout_s=60,
    )


def _worker(tmp_path: Path, api: RecordingApi, handler: Any) -> Worker:
    settings = WorkerSettings(
        api_url="http://api.test",
        worker_token=TOKEN,  # type: ignore[arg-type]
        work_dir=tmp_path / "work",
        progress_min_interval_seconds=0.2,
    )
    return Worker(settings, _client(api), {"test.job": handler})


@pytest.mark.parametrize(
    ("exc", "code", "retryable"),
    [
        (JobError("invalid_payload", "mal"), "invalid_payload", False),
        (ProcessFailedError(1, "error de ffmpeg"), "ffmpeg_failed", True),
        (RuntimeError("bug"), "worker_error", True),
    ],
)
def test_handler_errors_are_reported(
    tmp_path: Path, exc: Exception, code: str, retryable: bool
) -> None:
    api = RecordingApi()

    def handler(ctx: JobContext) -> HandlerResult:
        (ctx.work_dir / "tmp.bin").write_bytes(b"x")
        raise exc

    worker = _worker(tmp_path, api, handler)
    worker.execute(_job())
    assert api.paths()[-1] == "fail"
    body = api.body("/fail")
    assert (body["code"], body["retryable"]) == (code, retryable)
    assert list((tmp_path / "work").iterdir()) == []  # directorio aislado borrado


def test_successful_handler_completes(tmp_path: Path) -> None:
    api = RecordingApi()
    worker = _worker(tmp_path, api, lambda ctx: HandlerResult(outputs=[], result={"ok": True}))
    worker.execute(_job())
    assert api.paths()[-1] == "complete"
    assert api.body("/complete")["result"] == {"ok": True}


def test_cancel_requested_is_acknowledged(tmp_path: Path) -> None:
    api = RecordingApi(cancel=True)

    def handler(ctx: JobContext) -> HandlerResult:
        ctx.check_cancelled()
        return HandlerResult(outputs=[])

    worker = _worker(tmp_path, api, handler)
    worker.execute(_job())
    assert api.paths()[-1] == "cancelled"


def test_unknown_job_type_fails_without_retry(tmp_path: Path) -> None:
    api = RecordingApi()
    worker = _worker(tmp_path, api, lambda ctx: HandlerResult(outputs=[]))
    job = _job().model_copy(update={"type": "otro.tipo"})
    worker.execute(job)
    body = api.body("/fail")
    assert body["code"] == "unsupported_job_type"
    assert body["retryable"] is False


def test_context_paths_are_confined(tmp_path: Path) -> None:
    api = RecordingApi()

    def handler(ctx: JobContext) -> HandlerResult:
        ctx.path("../../fuera.mp4")
        return HandlerResult(outputs=[])

    worker = _worker(tmp_path, api, handler)
    worker.execute(_job())
    assert api.body("/fail")["code"] == "worker_error"
