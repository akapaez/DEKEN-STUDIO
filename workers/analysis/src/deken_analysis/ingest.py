"""Handler `media.ingest`: del original subido a un activo listo para la biblioteca.

1. Descarga el original (URL firmada) al directorio aislado del trabajo.
2. SHA-256 del original (detección de duplicados y prueba de integridad).
3. ffprobe + decodificación de una muestra: rechaza ficheros que no son vídeo.
4. Derivados: póster, tira de miniaturas, proxy H.264 de 540p y forma de onda.
5. Verificación local del proxy y subida. La API vuelve a verificar todo.

El original nunca se modifica: solo se lee.
"""

from __future__ import annotations

import json
import time

from deken_analysis.ffmpeg_ops import (
    decode_sample,
    poster_args,
    proxy_args,
    strip_args,
    waveform_peaks,
)
from deken_shared.jobs import ErrorCode, MediaIngestPayload
from deken_shared.media import check_video_spec
from deken_worker.process import ProcessFailedError, probe_file, run_ffmpeg, sha256_file
from deken_worker.runtime import HandlerResult, JobContext, JobError


def media_ingest(ctx: JobContext) -> HandlerResult:
    payload = MediaIngestPayload.model_validate(ctx.job.payload)
    settings = ctx.settings
    if len(ctx.job.inputs) != 1:
        raise JobError(ErrorCode.INVALID_PAYLOAD, "La ingesta necesita exactamente un original")
    source_input = ctx.job.inputs[0]
    started = time.monotonic()

    ctx.report(0.01, "Descargando el original")
    source = ctx.download_input(source_input, verify_sha256=False)
    size = source.stat().st_size

    ctx.report(0.15, "Calculando SHA-256 del original")
    sha256 = sha256_file(source)

    ctx.report(0.2, "Validando el contenido")
    try:
        summary = probe_file(settings.ffprobe_path, source, timeout_s=min(120.0, ctx.remaining_s))
    except ProcessFailedError as exc:
        raise JobError(
            ErrorCode.INVALID_MEDIA, f"No es un vídeo legible: {exc.stderr_tail[:300]}"
        ) from exc
    if not summary.video_streams:
        raise JobError(ErrorCode.INVALID_MEDIA, "El fichero no contiene vídeo")
    dynamic_range = summary.video_streams[0].dynamic_range or "sdr"
    hdr = dynamic_range != "sdr"
    try:
        warnings = decode_sample(
            settings.ffmpeg_path,
            source,
            cwd=ctx.work_dir,
            seconds=payload.decode_sample_s,
            timeout_s=min(600.0, ctx.remaining_s),
            cancel=ctx.cancel_event,
        )
    except ProcessFailedError as exc:
        raise JobError(
            ErrorCode.INVALID_MEDIA, f"El vídeo no se puede decodificar: {exc.stderr_tail[:300]}"
        ) from exc

    duration = payload.proxy.duration_s
    ctx.report(0.25, "Generando póster y miniaturas")
    run_ffmpeg(
        settings.ffmpeg_path,
        poster_args(
            source,
            "poster.jpg",
            at_s=min(1.0, duration * 0.1),
            max_px=payload.poster_max_px,
            hdr=hdr,
        ),
        cwd=ctx.work_dir,
        timeout_s=min(300.0, ctx.remaining_s),
        cancel=ctx.cancel_event,
    )
    run_ffmpeg(
        settings.ffmpeg_path,
        strip_args(
            source,
            "strip.jpg",
            frames=payload.strip_frames,
            duration_s=duration,
            height=payload.strip_height,
            hdr=hdr,
        ),
        cwd=ctx.work_dir,
        timeout_s=min(1800.0, ctx.remaining_s),
        cancel=ctx.cancel_event,
    )

    ctx.report(
        0.3,
        "Creando proxy de previsualización (540p"
        + (f", HDR {dynamic_range.upper()} → SDR BT.709)" if hdr else ")"),
    )
    proxy = payload.proxy
    run_ffmpeg(
        settings.ffmpeg_path,
        proxy_args(
            source,
            "proxy.mp4",
            width=proxy.width,
            height=proxy.height,
            fps=proxy.fps,
            has_audio=proxy.has_audio,
            hdr=hdr,
        ),
        cwd=ctx.work_dir,
        timeout_s=ctx.remaining_s,
        cancel=ctx.cancel_event,
        duration_s=duration,
        on_progress=lambda p: ctx.report(0.3 + 0.55 * p),
    )
    proxy_path = ctx.path("proxy.mp4")
    problems = check_video_spec(probe_file(settings.ffprobe_path, proxy_path), payload.proxy_spec())
    if problems:
        raise JobError(
            ErrorCode.LOCAL_VERIFICATION_FAILED,
            "El proxy no cumple la especificación",
            details={"problems": problems},
        )

    outputs = []
    waveform_points = 0
    if proxy.has_audio:
        ctx.report(0.86, "Calculando forma de onda")
        peaks = waveform_peaks(
            settings.ffmpeg_path,
            source,
            points=payload.waveform_points,
            duration_s=duration,
            timeout_s=min(1800.0, ctx.remaining_s),
            cancel=ctx.cancel_event,
        )
        waveform_points = len(peaks)
        ctx.path("waveform.json").write_text(
            json.dumps({"version": 1, "duration_s": duration, "peaks": peaks}), encoding="utf-8"
        )

    ctx.report(0.9, "Subiendo derivados")
    outputs.append(ctx.upload_output("poster", ctx.path("poster.jpg"), "image/jpeg"))
    outputs.append(ctx.upload_output("strip", ctx.path("strip.jpg"), "image/jpeg"))
    outputs.append(ctx.upload_output("proxy", proxy_path, "video/mp4"))
    if waveform_points:
        outputs.append(ctx.upload_output("waveform", ctx.path("waveform.json"), "application/json"))

    # El original sigue intacto: se comprueba que no ha cambiado durante el proceso.
    if sha256_file(source) != sha256:
        raise JobError(
            ErrorCode.WORKER_ERROR, "El original cambió durante la ingesta", retryable=True
        )

    return HandlerResult(
        outputs=outputs,
        result={
            "sha256": sha256,
            "size_bytes": size,
            "strip_frames": payload.strip_frames,
            "decode_sample_s": payload.decode_sample_s,
            "decode_warnings": len([line for line in warnings.splitlines() if line.strip()]),
            "waveform_points": waveform_points,
            "dynamic_range": dynamic_range,
            "tone_mapped": hdr,
            "proxy": proxy.model_dump(mode="json"),
            "elapsed_s": round(time.monotonic() - started, 2),
        },
    )
