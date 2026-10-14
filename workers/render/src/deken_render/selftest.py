"""Autotest de render: comprueba la cadena completa con una señal SINTÉTICA.

Genera barras de prueba (`testsrc2`) y un tono de 1 kHz, codifica H.264/AAC con los
mismos parámetros que usará el render real, verifica el fichero localmente (ffprobe +
decodificación completa) y lo sube. La API vuelve a verificarlo antes de aceptarlo.

No es contenido de DEKEN y se almacena bajo `system/`, separado del material real.
"""

from __future__ import annotations

import time

from deken_shared.jobs import ErrorCode, RenderSelftestPayload
from deken_shared.media import check_video_spec
from deken_worker.process import probe_file, run_ffmpeg, verify_decodes
from deken_worker.runtime import HandlerResult, JobContext, JobError

SYNTHETIC_COMMENT = "DEKEN STUDIO AI - autotest con señal sintética (no es contenido)"


def encode_args(payload: RenderSelftestPayload, output: str) -> list[str]:
    w, h, fps, d = payload.width, payload.height, payload.fps, payload.duration_s
    return [
        "-f", "lavfi", "-i", f"testsrc2=size={w}x{h}:rate={fps}:duration={d}",
        "-f", "lavfi", "-i", f"sine=frequency=1000:sample_rate=48000:duration={d}",
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "veryfast", "-profile:v", "high",
        "-pix_fmt", "yuv420p", "-r", str(fps), "-g", str(fps * 2),
        "-vf", "setsar=1",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
        "-t", str(d),
        "-movflags", "+faststart",
        "-metadata", f"title={payload.label}",
        "-metadata", f"comment={SYNTHETIC_COMMENT}",
        output,
    ]  # fmt: skip


def render_selftest(ctx: JobContext) -> HandlerResult:
    payload = RenderSelftestPayload.model_validate(ctx.job.payload)
    spec = payload.video_spec()
    output = ctx.path("autotest.mp4")
    settings = ctx.settings

    ctx.report(0.02, "Codificando señal sintética de prueba")
    started = time.monotonic()
    run_ffmpeg(
        settings.ffmpeg_path,
        encode_args(payload, output.name),
        cwd=ctx.work_dir,
        timeout_s=ctx.remaining_s,
        cancel=ctx.cancel_event,
        duration_s=payload.duration_s,
        on_progress=lambda p: ctx.report(0.02 + 0.68 * p),
    )
    encode_s = round(time.monotonic() - started, 3)

    ctx.report(0.72, "Verificando localmente (ffprobe y decodificación completa)")
    summary = probe_file(settings.ffprobe_path, output, timeout_s=min(60.0, ctx.remaining_s))
    problems = check_video_spec(summary, spec)
    if problems:
        raise JobError(
            ErrorCode.LOCAL_VERIFICATION_FAILED,
            "La salida no cumple la especificación",
            details={"problems": problems},
        )
    verify_decodes(
        settings.ffmpeg_path,
        output,
        cwd=ctx.work_dir,
        timeout_s=ctx.remaining_s,
        cancel=ctx.cancel_event,
    )

    ctx.report(0.85, "Subiendo resultado")
    declaration = ctx.upload_output("video", output, "video/mp4")
    ctx.report(0.97, "Esperando verificación del servidor")
    return HandlerResult(
        outputs=[declaration],
        result={
            "synthetic": True,
            "encoder": "libx264",
            "encode_seconds": encode_s,
            "spec": spec.model_dump(mode="json"),
            "local_probe": summary.model_dump(mode="json"),
        },
    )
