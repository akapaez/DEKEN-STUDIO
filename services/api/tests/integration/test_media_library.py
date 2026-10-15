"""Sprint 1 — Biblioteca audiovisual (S1-01 a S1-04) con servicios y worker reales.

Todos los vídeos son SINTÉTICOS (barras + tono generados con FFmpeg) y lo indican en sus
metadatos; ninguno es material de DEKEN.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

from deken_api.security.rbac import Role
from deken_api.testing import (
    ApiClient,
    ClientFactory,
    LiveServer,
    UserFactory,
    WorkerFactory,
    synthetic_video,
    upload_media,
)
from deken_shared.jobs import Queue
from deken_worker.client import WorkerClient
from deken_worker.config import WorkerSettings
from deken_worker.runtime import Worker, load_handlers

pytestmark = [pytest.mark.integration, pytest.mark.media]


@pytest.fixture
async def ingest_worker(
    live_server: LiveServer, make_worker: WorkerFactory, tmp_path: Path
) -> Worker:
    registered = await make_worker([Queue.ANALYSIS, Queue.RENDER])
    settings = WorkerSettings(
        api_url=live_server.url,
        worker_token=registered.token,  # type: ignore[arg-type]
        worker_queues=["analysis"],
        work_dir=tmp_path / "work",
        claim_wait_seconds=0,
    )
    worker = Worker(settings, WorkerClient(live_server.url, registered.token), load_handlers())
    yield worker  # type: ignore[misc]
    worker.client.close()


async def ingest(worker: Worker) -> bool:
    return await asyncio.to_thread(worker.run_once, 0)


async def asset(client: ApiClient, asset_id: str) -> dict[str, Any]:
    response = await client.get(f"/api/v1/media/assets/{asset_id}")
    assert response.status_code == 200, response.text
    return dict(response.json())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ffprobe(path: Path) -> dict[str, Any]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True,
        check=True,
    )
    return dict(json.loads(out.stdout))


async def download(url: str, dest: Path) -> Path:
    async with httpx.AsyncClient(timeout=120) as http:
        response = await http.get(url)
    assert response.status_code == 200
    dest.write_bytes(response.content)
    return dest


# --- S1-01 / S1-03 / S1-04: importación, originales intactos, derivados reales ----------------


async def test_vertical_mp4_import_and_ingest(
    admin_client: ApiClient, ingest_worker: Worker, tmp_path: Path
) -> None:
    source = synthetic_video(tmp_path / "vertical.mp4", width=1080, height=1920, seconds=3)
    before = sha256(source)

    completed = await upload_media(admin_client, source, title="Corte de perfiles (sintético)")
    assert completed.status_code == 200, completed.text
    data = completed.json()
    assert data["status"] == "processing"
    assert (data["width"], data["height"], data["orientation"]) == (1080, 1920, "vertical")
    assert data["has_audio"] is True
    assert data["original_object"]["status"] == "available"

    assert await ingest(ingest_worker) is True
    ready = await asset(admin_client, data["id"])
    assert ready["status"] == "ready", ready["status_reason"]
    assert ready["sha256"] == before
    assert ready["poster_url"] and ready["strip_url"] and ready["proxy_url"]
    assert ready["has_waveform"] is True
    assert ready["strip_frames"] == 10

    # Proxy real: 540x960, H.264, mismo aspecto, reproducible y completo.
    proxy = await download(ready["proxy_url"], tmp_path / "proxy.mp4")
    info = ffprobe(proxy)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    assert (video["codec_name"], video["width"], video["height"]) == ("h264", 540, 960)
    assert video.get("sample_aspect_ratio", "1:1") in {"1:1", "N/A"}
    assert any(s["codec_type"] == "audio" for s in info["streams"])
    subprocess.run(
        ["ffmpeg", "-v", "error", "-xerror", "-i", str(proxy), "-f", "null", "-"], check=True
    )

    poster = ffprobe(await download(ready["poster_url"], tmp_path / "poster.jpg"))["streams"][0]
    assert poster["codec_name"] == "mjpeg"
    assert (poster["width"], poster["height"]) == (405, 720)  # lado mayor 720, sin deformar
    strip = ffprobe(await download(ready["strip_url"], tmp_path / "strip.jpg"))["streams"][0]
    assert (strip["width"], strip["height"]) == (1010, 180)  # 10 miniaturas de 101x180

    waveform = await admin_client.get(f"/api/v1/media/assets/{data['id']}/waveform")
    assert waveform.status_code == 200
    peaks = waveform.json()["peaks"]
    assert 500 <= len(peaks) <= 1000 and max(peaks) > 0.1

    # S1-03: el original almacenado es idéntico byte a byte al fichero subido.
    link = await admin_client.get(f"/api/v1/media/assets/{data['id']}/original-url")
    original = await download(link.json()["url"], tmp_path / "original.mp4")
    assert sha256(original) == before
    assert sha256(source) == before


async def test_mov_without_audio_and_rotated_mov(
    admin_client: ApiClient, ingest_worker: Worker, tmp_path: Path
) -> None:
    horizontal = synthetic_video(
        tmp_path / "h.mov", width=1920, height=1080, seconds=2, audio=False
    )
    rotated = synthetic_video(
        tmp_path / "movil.mov", width=1280, height=720, seconds=2, rotation=90
    )

    h = (await upload_media(admin_client, horizontal)).json()
    r = (await upload_media(admin_client, rotated)).json()
    assert (h["width"], h["height"], h["has_audio"]) == (1920, 1080, False)
    # La rotación del móvil se respeta: se ve en vertical, no se deforma.
    assert (r["width"], r["height"], r["rotation"]) == (720, 1280, 90)

    assert await ingest(ingest_worker)
    assert await ingest(ingest_worker)
    h_ready = await asset(admin_client, h["id"])
    r_ready = await asset(admin_client, r["id"])
    assert h_ready["status"] == r_ready["status"] == "ready"
    assert h_ready["has_waveform"] is False

    h_proxy = ffprobe(await download(h_ready["proxy_url"], tmp_path / "hp.mp4"))
    assert [s["codec_type"] for s in h_proxy["streams"]] == ["video"]
    assert (h_proxy["streams"][0]["width"], h_proxy["streams"][0]["height"]) == (960, 540)
    r_proxy = ffprobe(await download(r_ready["proxy_url"], tmp_path / "rp.mp4"))
    rv = next(s for s in r_proxy["streams"] if s["codec_type"] == "video")
    assert (rv["width"], rv["height"]) == (540, 960)


@pytest.mark.skipif(
    os.environ.get("DEKEN_SKIP_LARGE") == "1", reason="omitido por DEKEN_SKIP_LARGE"
)
async def test_large_multipart_upload(
    admin_client: ApiClient, ingest_worker: Worker, tmp_path: Path
) -> None:
    """S1-01: fichero > 100 MB en varias partes de 16 MB.

    `DEKEN_LARGE_SECONDS` permite medir con ficheros mayores (480 s ≈ 2 GB)."""
    seconds = float(os.environ.get("DEKEN_LARGE_SECONDS", "26"))
    big = synthetic_video(
        tmp_path / "grande.mp4",
        width=1920,
        height=1080,
        seconds=seconds,
        audio=False,
        lossless=True,
    )
    size = big.stat().st_size
    assert size > 100 * 1024 * 1024
    start = await admin_client.post(
        "/api/v1/media/uploads", json={"filename": "grande.mp4", "size_bytes": size}
    )
    assert start.json()["part_count"] >= 7
    await admin_client.post(f"/api/v1/media/uploads/{start.json()['asset_id']}/abort")

    started = time.monotonic()
    completed = await upload_media(admin_client, big)
    uploaded = time.monotonic()
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "processing"
    assert await ingest(ingest_worker)
    ingested = time.monotonic()
    ready = await asset(admin_client, completed.json()["id"])
    assert ready["status"] == "ready", ready["status_reason"]
    assert ready["sha256"] == sha256(big)
    print(
        f"\n[medida] {size / 2**20:.0f} MiB, {seconds:.0f} s de vídeo: subida "
        f"{uploaded - started:.1f} s, ingesta {ingested - uploaded:.1f} s"
    )


# --- S1-02: validación del contenido --------------------------------------------------------------


async def test_fake_and_corrupt_files_are_rejected(
    admin_client: ApiClient, ingest_worker: Worker, tmp_path: Path, ctx: Any
) -> None:
    fake = tmp_path / "no-es-video.mp4"
    fake.write_text("Esto es texto con extensión .mp4\n" * 2000, encoding="utf-8")
    rejected = (await upload_media(admin_client, fake)).json()
    assert rejected["status"] == "rejected"
    assert (
        "vídeo" in rejected["status_reason"].lower()
        or "contenedor" in rejected["status_reason"].lower()
    )
    assert rejected["original_object"]["status"] == "deleted"

    good = synthetic_video(tmp_path / "base.mp4", width=640, height=360, seconds=6, lossless=True)
    data = bytearray(good.read_bytes())
    start = data.find(b"mdat") + 4
    data[start + 100 : start + 1_500_000] = os.urandom(1_500_000 - 100)
    corrupt = tmp_path / "corrupto.mp4"
    corrupt.write_bytes(bytes(data))

    accepted = (await upload_media(admin_client, corrupt)).json()
    assert accepted["status"] == "processing"  # las cabeceras son válidas
    assert await ingest(ingest_worker)
    final = await asset(admin_client, accepted["id"])
    assert final["status"] == "rejected"
    assert "decodificar" in final["status_reason"]


async def test_upload_validation_errors(admin_client: ApiClient, tmp_path: Path) -> None:
    bad_ext = await admin_client.post(
        "/api/v1/media/uploads", json={"filename": "clip.avi", "size_bytes": 1000}
    )
    assert bad_ext.status_code == 422
    assert bad_ext.json()["error"]["code"] == "unsupported_format"
    too_big = await admin_client.post(
        "/api/v1/media/uploads", json={"filename": "clip.mp4", "size_bytes": 21 * 1024**3}
    )
    assert too_big.status_code == 413
    source = synthetic_video(
        tmp_path / "parcial.mp4", width=1920, height=1080, seconds=6, lossless=True
    )
    incomplete = await upload_media(admin_client, source, skip_parts={2})
    if source.stat().st_size > 16 * 1024 * 1024:
        assert incomplete.status_code == 409
        assert incomplete.json()["error"]["code"] == "upload_incomplete"


# --- Duplicados ------------------------------------------------------------------------------


async def test_duplicates_are_detected(
    admin_client: ApiClient, ingest_worker: Worker, tmp_path: Path
) -> None:
    source = synthetic_video(tmp_path / "repetido.mp4", width=720, height=1280, seconds=2)
    first = (await upload_media(admin_client, source, title="Primero")).json()
    assert await ingest(ingest_worker)
    second = (await upload_media(admin_client, source, filename="copia.mp4", title="Copia")).json()
    assert await ingest(ingest_worker)
    dup = await asset(admin_client, second["id"])
    assert dup["status"] == "duplicate"
    assert dup["duplicate_of_id"] == first["id"]
    assert "Primero" in dup["status_reason"]
    assert (await asset(admin_client, first["id"]))["status"] == "ready"


# --- Catalogación, búsqueda, derechos y permisos ---------------------------------------------


async def test_catalog_search_and_filters(
    admin_client: ApiClient, ingest_worker: Worker, tmp_path: Path
) -> None:
    v = (
        await upload_media(
            admin_client,
            synthetic_video(tmp_path / "v.mp4", width=720, height=1280),
            title="Ensamblado de hoja",
        )
    ).json()
    h = (
        await upload_media(
            admin_client,
            synthetic_video(tmp_path / "h.mp4", width=1280, height=720, audio=False),
            title="Almacén",
        )
    ).json()
    assert await ingest(ingest_worker)
    assert await ingest(ingest_worker)

    tagged = await admin_client.patch(
        f"/api/v1/media/assets/{v['id']}",
        json={
            "tags": ["Fábrica", "ensamblado", "fábrica"],
            "location": "Santiponce",
            "description": "Línea 2",
        },
    )
    assert tagged.status_code == 200
    assert tagged.json()["tags"] == ["fábrica", "ensamblado"]
    bad = await admin_client.patch(f"/api/v1/media/assets/{v['id']}", json={"tags": ["<script>"]})
    assert bad.status_code == 422

    async def ids(**params: Any) -> list[str]:
        r = await admin_client.get("/api/v1/media/assets", params=params)
        assert r.status_code == 200
        return [i["id"] for i in r.json()["items"]]

    assert await ids(q="hoja") == [v["id"]]
    assert await ids(tag="fábrica") == [v["id"]]
    assert await ids(orientation="horizontal") == [h["id"]]
    assert await ids(has_audio="false") == [h["id"]]
    tags = (await admin_client.get("/api/v1/media/tags")).json()
    assert {"tag": "fábrica", "count": 1} in tags

    archived = await admin_client.post(f"/api/v1/media/assets/{h['id']}/archive")
    assert archived.json()["archived_at"] is not None
    assert h["id"] not in await ids()
    # Archivar no borra el original (inmutable).
    assert archived.json()["original_object"]["status"] == "available"


async def test_image_rights_workflow(
    admin_client: ApiClient,
    client_factory: ClientFactory,
    make_user: UserFactory,
    ingest_worker: Worker,
    tmp_path: Path,
) -> None:
    item = (await upload_media(admin_client, synthetic_video(tmp_path / "personas.mp4"))).json()
    assert await ingest(ingest_worker)
    ready = await asset(admin_client, item["id"])
    assert ready["people_present"] == "unknown"
    assert ready["usable_for_production"] is False

    editor, reviewer = await make_user(Role.EDITOR), await make_user(Role.REVIEWER)
    editor_client, reviewer_client = await client_factory(), await client_factory()
    await editor_client.login(editor.email)
    await reviewer_client.login(reviewer.email)

    denied = await editor_client.put(
        f"/api/v1/media/assets/{item['id']}/rights", json={"consent_status": "granted"}
    )
    assert denied.status_code == 403
    missing_ref = await reviewer_client.put(
        f"/api/v1/media/assets/{item['id']}/rights",
        json={"people_present": "yes", "consent_status": "granted"},
    )
    assert missing_ref.status_code == 422
    granted = await reviewer_client.put(
        f"/api/v1/media/assets/{item['id']}/rights",
        json={
            "people_present": "yes",
            "consent_status": "granted",
            "consent_reference": "RRHH-2026-014",
        },
    )
    assert granted.status_code == 200
    assert granted.json()["usable_for_production"] is True
    audit = (
        await admin_client.get("/api/v1/audit", params={"action": "media.rights_update"})
    ).json()
    assert audit["items"][0]["details"]["consent_status"] == {"from": "pending", "to": "granted"}


async def test_viewer_cannot_upload(client_factory: ClientFactory, make_user: UserFactory) -> None:
    viewer = await make_user(Role.VIEWER)
    client = await client_factory()
    await client.login(viewer.email)
    response = await client.post(
        "/api/v1/media/uploads", json={"filename": "a.mp4", "size_bytes": 10}
    )
    assert response.status_code == 403
    assert (await client.get("/api/v1/media/assets")).status_code == 200


async def test_iphone_hdr_mov_gets_sdr_previews(
    admin_client: ApiClient, ingest_worker: Worker, tmp_path: Path
) -> None:
    """MOV HEVC 10 bits HLG con rotación (como un iPhone): vistas previas en SDR BT.709."""
    source = synthetic_video(
        tmp_path / "IMG_0001.MOV", width=1280, height=720, seconds=2, rotation=90,
        pattern="smptebars", hdr_hlg=True,
    )  # fmt: skip
    before = sha256(source)
    uploaded = (await upload_media(admin_client, source)).json()
    assert uploaded["dynamic_range"] == "hlg"
    assert (uploaded["width"], uploaded["height"]) == (720, 1280)
    assert await ingest(ingest_worker)
    ready = await asset(admin_client, uploaded["id"])
    assert ready["status"] == "ready", ready["status_reason"]
    assert ready["sha256"] == before  # el original HDR no se toca

    proxy = ffprobe(await download(ready["proxy_url"], tmp_path / "proxy.mp4"))
    video = next(s for s in proxy["streams"] if s["codec_type"] == "video")
    assert (video["codec_name"], video["pix_fmt"], video["width"], video["height"]) == (
        "h264", "yuv420p", 540, 960,
    )  # fmt: skip
    assert (video.get("color_transfer"), video.get("color_primaries")) == ("bt709", "bt709")
    job = (await admin_client.get(f"/api/v1/jobs/{ready['ingest_job_id']}")).json()
    assert job["job"]["result"]["dynamic_range"] == "hlg"
    assert job["job"]["result"]["tone_mapped"] is True
