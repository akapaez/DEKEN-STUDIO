"""Comprobación del motor Remotion en esta máquina, sin API ni almacenamiento.

Renderiza la prueba técnica (5 s, 1080×1920, 30 fps, en modo evaluación) en un directorio
temporal, la verifica con ffprobe y decodificación completa y lo borra todo al terminar.

    deken-remotion-check            # imprime un JSON con el resultado; código 0 si pasa
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

from deken_render.remotion import (
    _versions,
    availability,
    remotion_settings,
    write_render_spec,
)
from deken_shared.jobs import RemotionEvalPayload
from deken_shared.media import check_video_spec
from deken_worker.process import probe_file, run_json_lines, verify_decodes


def run_check() -> dict[str, object]:
    settings = remotion_settings()
    ok, reason = availability(settings)
    if not ok:
        return {"ok": False, "stage": "availability", "reason": reason}
    payload = RemotionEvalPayload(label="Comprobación del motor")
    spec = payload.video_spec()
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="deken-remotion-check-") as tmp:
        work = Path(tmp)
        output = work / "render.mp4"
        spec_path = write_render_spec(
            settings,
            work,
            composition="DekenEvaluation",
            props=payload.model_dump(mode="json"),
            purpose="evaluation",
            output=output,
            inputs=[],
        )
        code, events, stderr = run_json_lines(
            [settings.node_path, str(settings.remotion_renderer), "--spec", spec_path.name],
            cwd=work,
            timeout_s=settings.remotion_timeout_ms / 1000 + 60,
        )
        final = events[-1] if events else {}
        if code != 0 or final.get("event") != "done":
            return {
                "ok": False,
                "stage": "render",
                "exit_code": code,
                "error": final,
                "stderr": stderr[-1500:],
            }
        summary = probe_file(settings.ffprobe_path, output, timeout_s=120)
        problems = check_video_spec(summary, spec)
        if problems:
            return {"ok": False, "stage": "verification", "problems": problems}
        verify_decodes(settings.ffmpeg_path, output, cwd=work, timeout_s=300)
        size = output.stat().st_size
    remotion, node = _versions(settings.node_path, settings.remotion_renderer)
    return {
        "ok": True,
        "remotion": remotion,
        "node": node,
        "license_mode": settings.remotion_license_mode,
        "size_bytes": size,
        "spec": spec.model_dump(mode="json"),
        "elapsed_s": round(time.monotonic() - started, 2),
    }


def main() -> None:
    result = run_check()
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
