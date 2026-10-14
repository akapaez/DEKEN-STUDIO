"""Motor Remotion en el worker: el handler Python lanza el renderer Node
(`workers/render/remotion`) como subproceso, con progreso por eventos JSON,
cancelación (SIGTERM → cancelSignal de Remotion) y timeout.

Puerta de licencia (ADR 0005): sin `DEKEN_REMOTION_LICENSE_MODE=company` y clave de
empresa, el worker solo ejecuta renders de evaluación (marca de agua, `evaluation/`).
Ningún secreto llega a la composición: solo rutas locales del directorio del trabajo.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from deken_shared.jobs import ErrorCode, RemotionEvalPayload, RenderTimelinePayload
from deken_shared.media import VideoSpec, check_video_spec
from deken_worker.process import probe_file, run_json_lines, verify_decodes
from deken_worker.runtime import HandlerResult, JobContext, JobError

RENDERER_DIR = Path(__file__).resolve().parents[2] / "remotion"

EXIT_CODES = {2: ErrorCode.INVALID_PAYLOAD, 3: ErrorCode.REMOTION_LICENSE_REQUIRED}
NON_RETRYABLE = {
    "invalid_spec",
    "invalid_timeline",
    "invalid_props",
    "unsafe_path",
    "remotion_license_required",
    "bundle_missing",
}


class RemotionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DEKEN_", extra="ignore")

    node_path: str = "node"
    remotion_renderer: Path = RENDERER_DIR / "dist" / "cli.js"
    remotion_bundle_dir: Path = RENDERER_DIR / "dist" / "bundle"
    remotion_browser: str | None = None
    remotion_license_mode: Literal["evaluation", "company"] = "evaluation"
    remotion_license_key: SecretStr | None = None
    remotion_concurrency: int | None = None
    remotion_timeout_ms: int = 300_000
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"


def remotion_settings() -> RemotionSettings:
    return RemotionSettings()


BROWSER_BINARIES = {"chrome-headless-shell", "headless_shell"}


def browser_path(settings: RemotionSettings) -> str | None:
    """Navegador configurado o, si no, el que instala `pnpm … browser` en el paquete del
    renderer. Nunca se deja que Remotion lo descargue en el directorio de un trabajo."""
    if settings.remotion_browser:
        return settings.remotion_browser
    cache = settings.remotion_renderer.resolve().parents[1] / "node_modules" / ".remotion"
    for candidate in sorted((cache / "chrome-headless-shell").glob("*/chrome-headless-shell-*/*")):
        if candidate.name in BROWSER_BINARIES and candidate.is_file():
            return str(candidate)
    return None


def availability(settings: RemotionSettings | None = None) -> tuple[bool, str]:
    s = settings or remotion_settings()
    node = shutil.which(s.node_path) if not Path(s.node_path).is_absolute() else s.node_path
    if not node or not Path(node).exists():
        return False, "Node.js no encontrado"
    if not s.remotion_renderer.exists():
        return False, f"renderer no compilado ({s.remotion_renderer})"
    if not (s.remotion_bundle_dir / "index.html").exists():
        return False, f"bundle de composiciones no generado ({s.remotion_bundle_dir})"
    browser = browser_path(s)
    if browser is None:
        return False, "navegador no instalado (pnpm --filter @deken/remotion-renderer browser)"
    if not Path(browser).exists():
        return False, f"navegador no encontrado ({browser})"
    return True, "ok"


@lru_cache(maxsize=4)
def _versions(node_path: str, renderer: Path) -> tuple[str | None, str | None]:
    remotion = None
    # dist/cli.js → <paquete del renderer>/node_modules/remotion
    pkg = renderer.resolve().parents[1] / "node_modules" / "remotion" / "package.json"
    if pkg.exists():
        remotion = str(json.loads(pkg.read_text("utf-8")).get("version"))
    try:
        node = (
            subprocess.run(  # noqa: S603 - lista de argumentos, sin shell
                [node_path, "--version"], capture_output=True, timeout=10, check=False, text=True
            ).stdout.strip()
            or None
        )
    except OSError:
        node = None
    return remotion, node


def describe_engine() -> dict[str, str]:
    """Información del motor para las capacidades del worker (heartbeat)."""
    settings = remotion_settings()
    ok, reason = availability(settings)
    if not ok:
        return {"remotion": f"no disponible: {reason}"}
    remotion, node = _versions(settings.node_path, settings.remotion_renderer)
    return {
        "remotion": remotion or "desconocida",
        "remotion_license": settings.remotion_license_mode,
        "node": node or "desconocida",
    }


def _license(settings: RemotionSettings) -> dict[str, Any]:
    license_info: dict[str, Any] = {"mode": settings.remotion_license_mode}
    if settings.remotion_license_mode == "company" and settings.remotion_license_key:
        license_info["key"] = settings.remotion_license_key.get_secret_value()
    return license_info


def write_render_spec(
    settings: RemotionSettings,
    work_dir: Path,
    *,
    composition: str,
    props: dict[str, Any],
    purpose: str,
    output: Path,
    inputs: list[dict[str, Any]],
) -> Path:
    """Escribe la especificación para el renderer Node (solo rutas locales, sin secretos de
    almacenamiento). Permisos 600: puede llevar la clave de licencia de empresa."""
    render_spec = {
        "composition": composition,
        "props": props,
        "purpose": purpose,
        "output_path": str(output),
        "work_dir": str(work_dir),
        "inputs": inputs,
        "license": _license(settings),
        "bundle_dir": str(settings.remotion_bundle_dir),
        "timeout_ms": settings.remotion_timeout_ms,
        **({"browser_executable": browser} if (browser := browser_path(settings)) else {}),
        **({"concurrency": settings.remotion_concurrency} if settings.remotion_concurrency else {}),
    }
    spec_path = work_dir / "render-spec.json"
    spec_path.touch(mode=0o600)
    spec_path.write_text(json.dumps(render_spec), encoding="utf-8")
    return spec_path


def _render(
    ctx: JobContext,
    *,
    composition: str,
    props: dict[str, Any],
    purpose: str,
    spec: VideoSpec,
    inputs: list[dict[str, Any]],
) -> HandlerResult:
    settings = remotion_settings()
    ok, reason = availability(settings)
    if not ok:
        raise JobError(
            ErrorCode.ENGINE_UNAVAILABLE, f"Remotion no disponible: {reason}", retryable=True
        )
    if purpose == "production" and settings.remotion_license_mode != "company":
        raise JobError(
            ErrorCode.REMOTION_LICENSE_REQUIRED,
            "Este worker no tiene licencia de empresa de Remotion: solo evaluación",
        )
    output = ctx.path("render.mp4")
    spec_path = write_render_spec(
        settings,
        ctx.work_dir,
        composition=composition,
        props=props,
        purpose=purpose,
        output=output,
        inputs=inputs,
    )

    ctx.report(0.05, "Renderizando con Remotion")
    started = time.monotonic()

    def on_event(event: dict[str, Any]) -> None:
        if event.get("event") == "progress":
            ctx.report(0.05 + 0.75 * float(event.get("progress") or 0))

    code, events, stderr = run_json_lines(
        [settings.node_path, str(settings.remotion_renderer), "--spec", spec_path.name],
        cwd=ctx.work_dir,
        timeout_s=ctx.remaining_s,
        cancel=ctx.cancel_event,
        on_event=on_event,
    )
    spec_path.unlink(missing_ok=True)
    final = events[-1] if events else {}
    if code != 0 or final.get("event") != "done":
        err_code = str(final.get("code") or EXIT_CODES.get(code, ErrorCode.RENDER_FAILED))
        message = str(final.get("message") or f"El renderer terminó con código {code}")
        raise JobError(
            err_code,
            message,
            retryable=err_code not in NON_RETRYABLE,
            details={"issues": final.get("details"), "stderr": stderr[-1500:]},
        )

    ctx.report(0.82, "Verificando el MP4 (ffprobe y decodificación completa)")
    ffmpeg = ctx.settings.ffmpeg_path
    summary = probe_file(ctx.settings.ffprobe_path, output, timeout_s=min(120.0, ctx.remaining_s))
    problems = check_video_spec(summary, spec)
    if problems:
        raise JobError(
            ErrorCode.LOCAL_VERIFICATION_FAILED,
            "El render no cumple la especificación",
            details={"problems": problems},
        )
    verify_decodes(
        ffmpeg, output, cwd=ctx.work_dir, timeout_s=ctx.remaining_s, cancel=ctx.cancel_event
    )

    ctx.report(0.9, "Subiendo el render")
    declaration = ctx.upload_output("video", output, "video/mp4")
    remotion, node = _versions(settings.node_path, settings.remotion_renderer)
    return HandlerResult(
        outputs=[declaration],
        result={
            "engine": "remotion",
            "engine_version": remotion,
            "node_version": node,
            "composition": composition,
            "purpose": purpose,
            "license_mode": settings.remotion_license_mode,
            "watermarked": purpose != "production",
            "render_ms": final.get("render_ms"),
            "elapsed_s": round(time.monotonic() - started, 2),
            "spec": spec.model_dump(mode="json"),
            "local_probe": summary.model_dump(mode="json"),
        },
    )


def remotion_eval(ctx: JobContext) -> HandlerResult:
    payload = RemotionEvalPayload.model_validate(ctx.job.payload)
    return _render(
        ctx,
        composition="DekenEvaluation",
        props=payload.model_dump(mode="json"),
        purpose="evaluation",
        spec=payload.video_spec(),
        inputs=[],
    )


def render_timeline(ctx: JobContext) -> HandlerResult:
    payload = RenderTimelinePayload.model_validate(ctx.job.payload)
    inputs: list[dict[str, Any]] = []
    for i, item in enumerate(ctx.job.inputs):
        ctx.report(0.01 + 0.03 * i / max(1, len(ctx.job.inputs)), f"Descargando {item.name}")
        path = ctx.download_input(item)
        inputs.append(
            {
                "key": item.key,
                "file": path.name,
                "kind": item.kind,
                **{
                    k: v
                    for k in ("width", "height", "duration_s", "has_audio")
                    if (v := getattr(item, k)) is not None
                },
            }
        )
    return _render(
        ctx,
        composition="DekenTimeline",
        props={"timeline": payload.timeline},
        purpose=payload.purpose,
        spec=payload.video_spec(),
        inputs=inputs,
    )
