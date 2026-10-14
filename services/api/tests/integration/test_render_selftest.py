"""S0-11: render real verificado de extremo a extremo.

API real por HTTP + worker real (proceso del runtime) + FFmpeg real + almacenamiento S3.
La señal es SINTÉTICA (barras y tono), como corresponde a una prueba técnica.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
from pathlib import Path

import httpx
import pytest

from deken_api.testing import ApiClient, LiveServer, WorkerFactory
from deken_render.handlers import HANDLERS
from deken_worker.client import WorkerClient
from deken_worker.config import WorkerSettings
from deken_worker.runtime import Worker

pytestmark = [pytest.mark.integration, pytest.mark.media]


def _worker(live_server: LiveServer, token: str, work_dir: Path) -> Worker:
    settings = WorkerSettings(
        api_url=live_server.url,
        worker_token=token,  # type: ignore[arg-type]
        worker_queues=["render"],
        work_dir=work_dir,
        claim_wait_seconds=0,
        progress_min_interval_seconds=0.2,
    )
    client = WorkerClient(settings.api_url, token)
    return Worker(settings, client, HANDLERS)


def _ffprobe(path: Path) -> dict[str, object]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        capture_output=True,
        check=True,
        timeout=60,
    )
    return dict(json.loads(out.stdout))


async def test_render_selftest_end_to_end(
    live_server: LiveServer,
    admin_client: ApiClient,
    make_worker: WorkerFactory,
    tmp_path: Path,
) -> None:
    registered = await make_worker()
    worker = _worker(live_server, registered.token, tmp_path / "work")

    job = (await admin_client.post("/api/v1/system/selftest", json={"duration_s": 2.0})).json()
    await asyncio.to_thread(worker.heartbeat)
    processed = await asyncio.to_thread(worker.run_once, 0)
    worker.client.close()
    assert processed is True

    detail = (await admin_client.get(f"/api/v1/jobs/{job['id']}")).json()
    assert detail["job"]["status"] == "completed", detail["job"]["error"]
    assert detail["job"]["progress"] == 1.0
    assert detail["job"]["result"]["synthetic"] is True
    kinds = [e["kind"] for e in detail["events"]]
    assert kinds[:2] == ["created", "claimed"]
    assert kinds[-1] == "completed"
    assert detail["outputs"][0]["verified"] is True
    # El directorio aislado del trabajo se ha borrado.
    assert list((tmp_path / "work").iterdir()) == []

    object_id = detail["outputs"][0]["stored_object"]["id"]
    link = (await admin_client.get(f"/api/v1/files/{object_id}/download-url")).json()
    async with httpx.AsyncClient() as http:
        response = await http.get(link["url"])
    assert response.status_code == 200
    downloaded = tmp_path / "descarga.mp4"
    downloaded.write_bytes(response.content)
    assert (
        hashlib.sha256(response.content).hexdigest()
        == detail["outputs"][0]["stored_object"]["sha256"]
    )

    probe = _ffprobe(downloaded)
    streams = probe["streams"]
    assert isinstance(streams, list)
    video = next(s for s in streams if s["codec_type"] == "video")
    audio = next(s for s in streams if s["codec_type"] == "audio")
    assert (video["codec_name"], video["width"], video["height"]) == ("h264", 1080, 1920)
    assert video["avg_frame_rate"] == "30/1"
    assert video["pix_fmt"] == "yuv420p"
    assert int(video["nb_frames"]) == 60
    assert (audio["codec_name"], audio["sample_rate"]) == ("aac", "48000")
    fmt = probe["format"]
    assert isinstance(fmt, dict)
    assert abs(float(fmt["duration"]) - 2.0) < 0.05
    # Integridad: se decodifica entero sin errores.
    subprocess.run(
        ["ffmpeg", "-v", "error", "-xerror", "-i", str(downloaded), "-f", "null", "-"],
        check=True,
        timeout=120,
    )


async def test_worker_honours_cancellation(
    live_server: LiveServer,
    admin_client: ApiClient,
    make_worker: WorkerFactory,
    tmp_path: Path,
) -> None:
    registered = await make_worker()
    worker = _worker(live_server, registered.token, tmp_path / "work")
    job = (await admin_client.post("/api/v1/system/selftest", json={"duration_s": 30.0})).json()

    async def cancel_soon() -> None:
        for _ in range(100):
            detail = (await admin_client.get(f"/api/v1/jobs/{job['id']}")).json()
            if detail["job"]["status"] == "processing":
                await admin_client.post(f"/api/v1/jobs/{job['id']}/cancel")
                return
            await asyncio.sleep(0.1)

    canceller = asyncio.create_task(cancel_soon())
    await asyncio.to_thread(worker.run_once, 0)
    await canceller
    worker.client.close()
    detail = (await admin_client.get(f"/api/v1/jobs/{job['id']}")).json()
    assert detail["job"]["status"] == "cancelled"
    assert detail["outputs"] == []
