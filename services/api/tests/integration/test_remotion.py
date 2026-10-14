"""Remotion como motor de composición: renders reales verificados de extremo a extremo.

API real + worker real (runtime + handler Remotion → renderer Node + Chromium) + S3.
Solo recursos SINTÉTICOS. Mientras la licencia de empresa no esté verificada
(`DEKEN_REMOTION_LICENSE_MODE=evaluation`), todo render es de evaluación, con marca de agua
y guardado en `evaluation/`.

Se omite si el motor no está disponible en esta máquina (Node, renderer compilado, bundle).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest

from deken_api.context import AppContext
from deken_api.db.models import StoredObject
from deken_api.testing import (
    ApiClient,
    LiveServer,
    WorkerFactory,
    synthetic_video,
    upload_media,
)
from deken_render.remotion import availability
from deken_shared.jobs import Queue
from deken_worker.client import WorkerClient
from deken_worker.config import WorkerSettings
from deken_worker.runtime import Worker, load_handlers

_available, _reason = availability()
# En CI (DEKEN_REQUIRE_REMOTION=1) no se omite nunca: si el motor falta, los tests fallan.
_required = os.environ.get("DEKEN_REQUIRE_REMOTION") == "1"
pytestmark = [
    pytest.mark.integration,
    pytest.mark.media,
    pytest.mark.skipif(not (_available or _required), reason=f"Remotion no disponible: {_reason}"),
]

FPS = 30


@pytest.fixture
async def worker(live_server: LiveServer, make_worker: WorkerFactory, tmp_path: Path) -> Worker:
    registered = await make_worker([Queue.ANALYSIS, Queue.RENDER])
    settings = WorkerSettings(
        api_url=live_server.url,
        worker_token=registered.token,  # type: ignore[arg-type]
        worker_queues=["analysis", "render"],
        work_dir=tmp_path / "work",
        claim_wait_seconds=0,
        progress_min_interval_seconds=0.2,
    )
    w = Worker(settings, WorkerClient(live_server.url, registered.token), load_handlers())
    yield w  # type: ignore[misc]
    w.client.close()


async def run_once(worker: Worker) -> bool:
    return await asyncio.to_thread(worker.run_once, 0)


async def job_detail(client: ApiClient, job_id: str) -> dict[str, Any]:
    response = await client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200, response.text
    return dict(response.json())


async def download_output(client: ApiClient, detail: dict[str, Any], dest: Path) -> Path:
    output = detail["outputs"][0]
    link = (await client.get(f"/api/v1/files/{output['stored_object']['id']}/download-url")).json()
    async with httpx.AsyncClient(timeout=120) as http:
        response = await http.get(link["url"])
    assert response.status_code == 200
    assert hashlib.sha256(response.content).hexdigest() == output["stored_object"]["sha256"]
    dest.write_bytes(response.content)
    return dest


def probe(path: Path) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any]]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json",
         str(path)],
        capture_output=True, check=True, timeout=120,
    )  # fmt: skip
    data = json.loads(out.stdout)
    video = next(s for s in data["streams"] if s["codec_type"] == "video")
    audio = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    return video, audio, data["format"]


def decodes_cleanly(path: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"],
        check=True,
        timeout=180,
    )


def text_only_timeline(*, seconds: float = 3, text_frames: int = 90) -> dict[str, Any]:
    return {
        "schema": "deken.timeline/1",
        "output": {
            "format": "vertical_9_16",
            "width": 1080,
            "height": 1920,
            "fps": FPS,
            "duration_frames": round(seconds * FPS),
        },
        "tracks": [
            {
                "id": "textos",
                "kind": "text",
                "clips": [
                    {
                        "id": "titulo",
                        "text": "Prueba sintética",
                        "at_frame": 0,
                        "duration_frames": text_frames,
                        "size_px": 96,
                    },
                ],
            }
        ],
    }


# --- Estado del motor y puerta de licencia ---------------------------------------------------


def test_engine_is_available() -> None:
    assert _available, _reason


async def test_engine_status_and_worker_capabilities(
    admin_client: ApiClient, worker: Worker
) -> None:
    await asyncio.to_thread(worker.heartbeat)
    engine = (await admin_client.get("/api/v1/renders/engine")).json()
    assert engine["license_mode"] == "evaluation"
    assert engine["commercial_renders_enabled"] is False
    assert len(engine["workers_with_remotion"]) == 1
    assert "pendiente" in engine["note"]

    (registered,) = (await admin_client.get("/api/v1/workers")).json()
    caps = registered["capabilities"]
    assert {"system.remotion_eval", "render.timeline", "media.ingest"} <= set(caps["job_types"])
    assert caps["engines"]["remotion"].startswith("4.")
    assert caps["engines"]["remotion_license"] == "evaluation"

    status = (await admin_client.get("/api/v1/system/status")).json()
    assert status["remotion"] == {"license_mode": "evaluation", "commercial_renders_enabled": False}


async def test_production_renders_are_blocked_without_company_license(
    admin_client: ApiClient,
) -> None:
    response = await admin_client.post(
        "/api/v1/renders/timeline", json={"timeline": text_only_timeline(), "purpose": "production"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "remotion_license_required"
    jobs = (await admin_client.get("/api/v1/jobs")).json()
    assert jobs["items"] == []


# --- Prueba técnica: 5 s, 1080×1920, 30 fps ----------------------------------------------------


async def test_remotion_evaluation_render_end_to_end(
    admin_client: ApiClient, worker: Worker, ctx: AppContext, tmp_path: Path
) -> None:
    created = await admin_client.post(
        "/api/v1/renders/evaluation",
        json={"title": "DEKEN STUDIO AI", "subtitle": "Prueba técnica"},
    )
    assert created.status_code == 201, created.text
    job = created.json()
    assert job["type"] == "system.remotion_eval"

    assert await run_once(worker) is True
    detail = await job_detail(admin_client, job["id"])
    assert detail["job"]["status"] == "completed", detail["job"]["error"]
    result = detail["job"]["result"]
    assert result["engine"] == "remotion"
    assert result["engine_version"].startswith("4.")
    assert (result["purpose"], result["license_mode"]) == ("evaluation", "evaluation")
    assert result["watermarked"] is True

    stored = detail["outputs"][0]["stored_object"]
    assert stored["kind"] == "evaluation"  # separado del contenido comercial
    async with ctx.sessionmaker() as db:
        obj = await db.get(StoredObject, uuid.UUID(stored["id"]))
    assert obj is not None and obj.key.startswith("evaluation/")
    assert detail["outputs"][0]["verified"] is True
    # Directorio del trabajo limpio (sin render-spec.json ni temporales).
    assert list((tmp_path / "work").iterdir()) == []

    mp4 = await download_output(admin_client, detail, tmp_path / "evaluacion.mp4")
    video, audio, fmt = probe(mp4)
    assert (video["codec_name"], video["width"], video["height"]) == ("h264", 1080, 1920)
    assert video["avg_frame_rate"] == "30/1"
    assert video["pix_fmt"] == "yuv420p"
    assert int(video["nb_read_frames"]) == 150
    assert video.get("sample_aspect_ratio", "1:1") in {"1:1", "N/A"}
    assert audio is not None and audio["codec_name"] == "aac"
    assert abs(float(fmt["duration"]) - 5.0) < 0.05
    decodes_cleanly(mp4)


# --- Línea de tiempo con un medio real ingerido -------------------------------------------------


async def test_timeline_render_reframes_horizontal_source_without_distortion(
    admin_client: ApiClient, worker: Worker, tmp_path: Path
) -> None:
    source = synthetic_video(tmp_path / "horizontal.mp4", width=1280, height=720, seconds=3)
    uploaded = (await upload_media(admin_client, source, title="Horizontal (sintético)")).json()
    assert await run_once(worker) is True  # ingesta
    asset_id = uploaded["id"]
    assert (await admin_client.get(f"/api/v1/media/assets/{asset_id}")).json()["status"] == "ready"

    crop_w = (720 * 9 / 16) / 1280  # recorte 9:16 a altura completa, sin estirar
    timeline: dict[str, Any] = {
        "schema": "deken.timeline/1",
        "template": "reel_vertical",
        "output": {"format": "vertical_9_16", "width": 1080, "height": 1920, "fps": FPS,
                   "duration_frames": 90},
        "tracks": [
            {"id": "video", "kind": "video", "clips": [
                {"id": "plano1", "asset_id": asset_id, "source_in_s": 0, "source_out_s": 3,
                 "at_frame": 0, "reframe": {"x": (1 - crop_w) / 2, "y": 0, "w": crop_w, "h": 1}},
            ]},
            {"id": "textos", "kind": "text", "clips": [
                {"id": "t1", "text": "Corte de perfiles", "at_frame": 0, "duration_frames": 90,
                 "size_px": 72, "position": "bottom"},
            ]},
        ],
    }  # fmt: skip
    created = await admin_client.post(
        "/api/v1/renders/timeline", json={"timeline": timeline, "title": "Reel de prueba"}
    )
    assert created.status_code == 201, created.text
    job = created.json()
    assert job["payload"]["purpose"] == "evaluation"
    assert job["payload"]["inputs"][0]["key"] == f"asset:{asset_id}"
    # Ni URLs ni claves de almacenamiento en la línea de tiempo guardada.
    assert "http" not in json.dumps(job["payload"]["timeline"])

    assert await run_once(worker) is True
    detail = await job_detail(admin_client, job["id"])
    assert detail["job"]["status"] == "completed", detail["job"]["error"]
    assert detail["outputs"][0]["stored_object"]["kind"] == "evaluation"
    assert list((tmp_path / "work").iterdir()) == []

    mp4 = await download_output(admin_client, detail, tmp_path / "reel.mp4")
    video, audio, fmt = probe(mp4)
    assert (video["width"], video["height"], video["avg_frame_rate"]) == (1080, 1920, "30/1")
    assert int(video["nb_read_frames"]) == 90
    assert audio is not None  # audio original del clip
    assert abs(float(fmt["duration"]) - 3.0) < 0.05
    decodes_cleanly(mp4)


async def test_timeline_validation_and_authorization(
    admin_client: ApiClient, worker: Worker, tmp_path: Path
) -> None:
    broken = text_only_timeline()
    broken["output"]["width"] = 1000  # no corresponde a 9:16
    schema = await admin_client.post("/api/v1/renders/timeline", json={"timeline": broken})
    assert schema.status_code == 422
    assert schema.json()["error"]["code"] == "invalid_timeline"

    unknown = text_only_timeline()
    unknown["tracks"].append(
        {"id": "v", "kind": "video", "clips": [
            {"id": "c", "asset_id": str(uuid.uuid4()), "source_in_s": 0, "source_out_s": 1,
             "at_frame": 0},
        ]}
    )  # fmt: skip
    unauthorized = await admin_client.post("/api/v1/renders/timeline", json={"timeline": unknown})
    assert unauthorized.status_code == 422
    assert unauthorized.json()["error"]["code"] == "unauthorized_media"

    # Medio subido pero aún en ingesta: tampoco se puede usar.
    pending = (
        await upload_media(admin_client, synthetic_video(tmp_path / "p.mp4", seconds=1))
    ).json()
    unknown["tracks"][1]["clips"][0]["asset_id"] = pending["id"]
    not_ready = await admin_client.post("/api/v1/renders/timeline", json={"timeline": unknown})
    assert not_ready.status_code == 422

    # Esquema válido pero semántica inválida (texto 1 s < 2,5 s mínimos de lectura):
    # el renderer lo rechaza y el trabajo falla sin reintentos.
    assert await run_once(worker) is True  # vacía la ingesta pendiente
    created = await admin_client.post(
        "/api/v1/renders/timeline", json={"timeline": text_only_timeline(text_frames=30)}
    )
    assert created.status_code == 201
    assert await run_once(worker) is True
    detail = await job_detail(admin_client, created.json()["id"])
    assert detail["job"]["status"] == "failed"
    assert detail["job"]["error"]["code"] == "invalid_timeline"
    assert detail["job"]["error"]["retryable"] is False
    assert detail["job"]["attempts"] == 1
    assert detail["outputs"] == []
    assert list((tmp_path / "work").iterdir()) == []


async def test_render_cancellation_stops_remotion(
    admin_client: ApiClient, worker: Worker, tmp_path: Path
) -> None:
    job = (
        await admin_client.post(
            "/api/v1/renders/timeline", json={"timeline": text_only_timeline(seconds=60)}
        )
    ).json()

    async def cancel_when_rendering() -> None:
        for _ in range(600):
            detail = await job_detail(admin_client, job["id"])
            if detail["job"]["status"] == "processing" and detail["job"]["progress"] >= 0.05:
                await admin_client.post(f"/api/v1/jobs/{job['id']}/cancel")
                return
            await asyncio.sleep(0.1)

    canceller = asyncio.create_task(cancel_when_rendering())
    await run_once(worker)
    await canceller
    detail = await job_detail(admin_client, job["id"])
    assert detail["job"]["status"] == "cancelled"
    assert detail["outputs"] == []
    assert list((tmp_path / "work").iterdir()) == []
