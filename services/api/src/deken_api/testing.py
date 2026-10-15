"""Utilidades de prueba compartidas (tests de integración y E2E).

Solo se usan desde `tests/`; no forman parte del camino de producción.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

import httpx

from deken_api.cli import alembic_config
from deken_api.security.rbac import Role
from deken_api.security.tokens import CSRF_HEADER
from deken_shared.jobs import CONTRACT_HEADER, JOB_CONTRACT_VERSION

TEST_PASSWORD = "Prueba-Integracion-2026"  # noqa: S105 - credencial de pruebas
ORIGIN = "http://localhost:3000"


@dataclass
class TestUser:
    __test__ = False  # no es una clase de tests de pytest

    id: uuid.UUID
    email: str
    role: Role
    password: str = TEST_PASSWORD


class ApiClient(httpx.AsyncClient):
    """Cliente con cookies de sesión y cabecera CSRF tras el login."""

    async def login(self, email: str, password: str = TEST_PASSWORD) -> httpx.Response:
        response = await self.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
            headers={"Origin": ORIGIN},
        )
        if response.status_code == 200:
            self.headers[CSRF_HEADER] = response.json()["csrf_token"]
        return response


@dataclass
class TestWorker:
    __test__ = False

    id: uuid.UUID
    token: str

    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            CONTRACT_HEADER: str(JOB_CONTRACT_VERSION),
        }


@dataclass
class LiveServer:
    url: str


ClientFactory = Callable[[], Awaitable[ApiClient]]
UserFactory = Callable[..., Awaitable[TestUser]]
WorkerFactory = Callable[..., Awaitable[TestWorker]]


T = TypeVar("T")


def run_sync[T](coro: Coroutine[Any, Any, T]) -> T:
    """Ejecuta una corrutina en un hilo con su propio bucle (válido aunque ya haya uno)."""
    import asyncio

    result: list[T] = []
    errors: list[BaseException] = []

    def _target() -> None:
        try:
            result.append(asyncio.run(coro))
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=_target)
    thread.start()
    thread.join()
    if errors:
        raise errors[0]
    return result[0]


def run_alembic(database_url: str, action: str, revision: str | None = None) -> None:
    """Ejecuta un comando de Alembic en un hilo propio (env.py usa asyncio.run)."""
    from alembic import command
    from alembic.config import Config

    errors: list[BaseException] = []

    def _target() -> None:
        try:
            cfg = alembic_config()
            if not isinstance(cfg, Config):  # pragma: no cover
                raise TypeError("configuración de Alembic inesperada")
            cfg.attributes["database_url"] = database_url
            func = getattr(command, action)
            if revision is None:
                func(cfg)
            else:
                func(cfg, revision)
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=_target)
    thread.start()
    thread.join()
    if errors:
        raise errors[0]


# --- Ficheros SINTÉTICOS de prueba (Sprint 1) ---------------------------------------------
# Todos llevan la etiqueta "SINTÉTICO" en sus metadatos: no son material de DEKEN.

SYNTHETIC_LABEL = "DEKEN STUDIO AI - fichero SINTÉTICO de prueba"


def synthetic_video(
    path: Path,
    *,
    width: int = 1080,
    height: int = 1920,
    seconds: float = 2.0,
    audio: bool = True,
    lossless: bool = False,
    rotation: int | None = None,
    fps: int = 30,
    pattern: str = "testsrc2",
    hdr_hlg: bool = False,
) -> Path:
    """Genera un vídeo de prueba real (barras + tono) con FFmpeg.

    `hdr_hlg`: las mismas barras codificadas como HLG BT.2020 en HEVC 10 bits (como un
    iPhone reciente), para comprobar el mapeo de tono frente a la versión SDR."""
    import subprocess

    target = path if rotation is None else path.with_suffix(".tmp" + path.suffix)
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", f"{pattern}=size={width}x{height}:rate={fps}:duration={seconds}",
    ]  # fmt: skip
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={seconds}"]
    if hdr_hlg:
        cmd += [
            "-vf",
            "format=gbrpf32le,zscale=tin=bt709:t=arib-std-b67:pin=bt709:p=bt2020:min=bt709:"
            "m=bt2020nc:r=tv,format=yuv420p10le",
            "-c:v", "libx265", "-preset", "ultrafast", "-x265-params", "log-level=error",
            "-tag:v", "hvc1", "-color_primaries", "bt2020", "-color_trc", "arib-std-b67",
            "-colorspace", "bt2020nc",
        ]  # fmt: skip
    else:
        cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]
    if not hdr_hlg:
        cmd += ["-qp", "0"] if lossless else ["-crf", "30"]
    cmd += ["-c:a", "aac", "-shortest"] if audio else ["-an"]
    cmd += ["-metadata", f"comment={SYNTHETIC_LABEL}", str(target)]
    subprocess.run(cmd, check=True, timeout=300)
    if rotation is not None:
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-display_rotation",
                str(rotation),
                "-i",
                str(target),
                "-c",
                "copy",
                str(path),
            ],
            check=True,
            timeout=120,
        )
        target.unlink()
    return path


def synthetic_logo(
    path: Path, *, width: int, height: int, inks: list[tuple[str, float]], alpha: bool = True
) -> Path:
    """Logo de prueba: franjas de tinta plana sobre fondo transparente."""
    from PIL import Image, ImageDraw

    image = Image.new(
        "RGBA" if alpha else "RGB", (width, height), (0, 0, 0, 0) if alpha else (255, 255, 255)
    )
    draw = ImageDraw.Draw(image)
    x = 0
    for color, share in inks:
        w = round(width * share)
        draw.rectangle([x, height // 5, x + w - 1, height - height // 5], fill=color)
        x += w
    image.save(path)
    return path


def synthetic_font(path: Path, *, family: str = "Sintetica Prueba", weight: int = 900) -> Path:
    """Tipografía TTF mínima generada con fontTools (solo para pruebas)."""
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder([".notdef", "A"])
    fb.setupCharacterMap({ord("A"): "A"})
    pen = TTGlyphPen(None)
    pen.moveTo((100, 0))
    pen.lineTo((500, 700))
    pen.lineTo((900, 0))
    pen.closePath()
    glyph = pen.glyph()
    fb.setupGlyf({".notdef": glyph, "A": glyph})
    fb.setupHorizontalMetrics({".notdef": (1000, 100), "A": (1000, 100)})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": family, "styleName": "Black"})
    fb.setupOS2(usWeightClass=weight)
    fb.setupPost()
    fb.save(str(path))
    return path


async def upload_media(
    client: httpx.AsyncClient,
    path: Path,
    *,
    filename: str | None = None,
    title: str | None = None,
    skip_parts: set[int] | None = None,
) -> httpx.Response:
    """Recorrido completo de subida multiparte como lo hace el navegador."""
    size = path.stat().st_size
    start = await client.post(
        "/api/v1/media/uploads",
        json={"filename": filename or path.name, "size_bytes": size, "title": title},
    )
    if start.status_code != 201:
        return start
    plan = start.json()
    asset_id, part_size, count = plan["asset_id"], plan["part_size_bytes"], plan["part_count"]
    numbers = [n for n in range(1, count + 1) if n not in (skip_parts or set())]
    urls: dict[int, str] = {}
    for i in range(0, len(numbers), plan["max_parts_per_request"]):
        resp = await client.post(
            f"/api/v1/media/uploads/{asset_id}/parts",
            json={"part_numbers": numbers[i : i + plan["max_parts_per_request"]]},
        )
        resp.raise_for_status()
        urls.update({p["part_number"]: p["url"] for p in resp.json()})
    async with httpx.AsyncClient(timeout=120) as storage:
        with path.open("rb") as fh:
            for n in range(1, count + 1):
                chunk = fh.read(part_size)
                if n in urls:
                    put = await storage.put(urls[n], content=chunk)
                    put.raise_for_status()
    return await client.post(f"/api/v1/media/uploads/{asset_id}/complete")


async def upload_brand(
    client: httpx.AsyncClient,
    path: Path,
    *,
    kind: str = "logo",
    name: str | None = None,
    filename: str | None = None,
    **extra: Any,
) -> httpx.Response:
    """Subida de un recurso de marca (PUT firmado directo al almacenamiento)."""
    data = path.read_bytes()
    start = await client.post(
        "/api/v1/brand/uploads",
        json={
            "kind": kind,
            "name": name or path.stem,
            "filename": filename or path.name,
            "size_bytes": len(data),
            **extra,
        },
    )
    if start.status_code != 201:
        return start
    plan = start.json()
    async with httpx.AsyncClient(timeout=60) as storage:
        put = await storage.put(plan["upload_url"], content=data, headers=plan["headers"])
        put.raise_for_status()
    return await client.post(f"/api/v1/brand/uploads/{plan['asset_id']}/complete")
