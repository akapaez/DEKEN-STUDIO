"""Cliente HTTP del protocolo de workers v1. Solo conexiones salientes."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID

import httpx
from pydantic import BaseModel

from deken_shared.jobs import (
    CONTRACT_HEADER,
    JOB_CONTRACT_VERSION,
    ClaimedJob,
    ClaimRequest,
    CompleteRequest,
    FailRequest,
    JobTransitionAck,
    LeaseAck,
    OutputUploadRequest,
    OutputUploadTicket,
    ProgressReport,
    WorkerHeartbeat,
    WorkerHeartbeatAck,
)
from deken_worker import __version__

T = TypeVar("T", bound=BaseModel)

RETRY_STATUSES = {502, 503, 504}
UPLOAD_CHUNK = 1024 * 1024


class ApiClientError(RuntimeError):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(f"{status} {code}: {message}")
        self.status = status
        self.code = code
        self.message = message


class LeaseLostError(ApiClientError):
    """La API ya no considera a este worker dueño del trabajo (cancelado, expirado...)."""


def _error_from(response: httpx.Response) -> ApiClientError:
    code, message = "http_error", response.text[:300]
    try:
        body = response.json()
        code = body["error"]["code"]
        message = body["error"]["message"]
    except (ValueError, KeyError, TypeError):
        pass
    cls = LeaseLostError if code == "lease_lost" else ApiClientError
    return cls(response.status_code, code, message)


class WorkerClient:
    def __init__(
        self,
        api_url: str,
        token: str,
        *,
        timeout: float = 60.0,
        verify: str | bool = True,
        transport: httpx.BaseTransport | None = None,
        retries: int = 4,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._http = httpx.Client(
            base_url=f"{api_url}/api/v1",
            headers={
                "Authorization": f"Bearer {token}",
                CONTRACT_HEADER: str(JOB_CONTRACT_VERSION),
                "User-Agent": f"deken-worker/{__version__}",
            },
            timeout=timeout,
            verify=verify,
            transport=transport,
        )
        # Cliente separado para URLs firmadas: NUNCA envía el token del worker al storage.
        self._storage = httpx.Client(timeout=timeout, verify=verify, transport=transport)
        self._retries = retries
        self._sleep = sleep

    def close(self) -> None:
        self._http.close()
        self._storage.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: BaseModel | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        kwargs: dict[str, Any] = {}
        if body is not None:
            kwargs["json"] = body.model_dump(mode="json")
        if timeout is not None:
            kwargs["timeout"] = timeout
        attempt = 0
        while True:
            try:
                response = self._http.request(method, path, **kwargs)
            except httpx.TransportError:
                if attempt >= self._retries:
                    raise
            else:
                if response.status_code not in RETRY_STATUSES or attempt >= self._retries:
                    return response
            attempt += 1
            self._sleep(min(30.0, 2.0**attempt))

    def _call(self, model: type[T], method: str, path: str, **kwargs: Any) -> T:
        response = self._request(method, path, **kwargs)
        if response.status_code >= 400:
            raise _error_from(response)
        return model.model_validate(response.json())

    # --- Protocolo -------------------------------------------------------------------

    def heartbeat(self, hb: WorkerHeartbeat) -> WorkerHeartbeatAck:
        return self._call(WorkerHeartbeatAck, "POST", "/worker/heartbeat", body=hb)

    def claim(self, req: ClaimRequest) -> ClaimedJob | None:
        response = self._request(
            "POST", "/worker/jobs/claim", body=req, timeout=req.wait_seconds + 30.0
        )
        if response.status_code == 204:
            return None
        if response.status_code >= 400:
            raise _error_from(response)
        return ClaimedJob.model_validate(response.json())

    def progress(self, job_id: UUID, report: ProgressReport) -> LeaseAck:
        return self._call(LeaseAck, "POST", f"/worker/jobs/{job_id}/progress", body=report)

    def request_output(self, job_id: UUID, req: OutputUploadRequest) -> OutputUploadTicket:
        return self._call(OutputUploadTicket, "POST", f"/worker/jobs/{job_id}/outputs", body=req)

    def complete(self, job_id: UUID, req: CompleteRequest) -> JobTransitionAck:
        return self._call(
            JobTransitionAck, "POST", f"/worker/jobs/{job_id}/complete", body=req, timeout=600.0
        )

    def fail(self, job_id: UUID, req: FailRequest) -> JobTransitionAck:
        return self._call(JobTransitionAck, "POST", f"/worker/jobs/{job_id}/fail", body=req)

    def ack_cancel(self, job_id: UUID) -> JobTransitionAck:
        return self._call(JobTransitionAck, "POST", f"/worker/jobs/{job_id}/cancelled")

    # --- Transferencias con URLs firmadas ---------------------------------------------

    def upload(self, ticket: OutputUploadTicket, path: Path) -> None:
        size = path.stat().st_size

        def chunks() -> Iterator[bytes]:
            with path.open("rb") as fh:
                while chunk := fh.read(UPLOAD_CHUNK):
                    yield chunk

        headers = {**ticket.headers, "Content-Length": str(size)}
        response = self._storage.request(
            ticket.method, ticket.upload_url, content=chunks(), headers=headers, timeout=None
        )
        if response.status_code >= 300:
            raise ApiClientError(response.status_code, "upload_failed", response.text[:300])

    def download(self, url: str, dest: Path) -> None:
        with self._storage.stream("GET", url, timeout=None) as response:
            if response.status_code >= 300:
                raise ApiClientError(response.status_code, "download_failed", "descarga fallida")
            with dest.open("wb") as fh:
                for chunk in response.iter_bytes(UPLOAD_CHUNK):
                    fh.write(chunk)
