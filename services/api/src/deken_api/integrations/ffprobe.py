"""Ejecución segura de ffprobe desde la API.

- Lista de argumentos (sin shell).
- Solo se permiten los protocolos necesarios para leer una URL firmada del
  almacenamiento propio.
- Timeout estricto; el proceso se mata si lo supera.
"""

from __future__ import annotations

import asyncio
import json
import re

from deken_shared.media import ProbeSummary, parse_ffprobe_json

URL_PROTOCOLS = "http,https,tcp,tls,crypto"


class ProbeError(RuntimeError):
    pass


async def _run(args: list[str], timeout_s: float) -> tuple[int, bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except TimeoutError:
        proc.kill()
        await proc.wait()
        raise ProbeError(f"ffprobe superó el tiempo límite de {timeout_s:.0f}s") from None
    return proc.returncode or 0, stdout, stderr


async def probe_url(ffprobe_path: str, url: str, *, timeout_s: float) -> ProbeSummary:
    if not url.startswith(("http://", "https://")):
        raise ProbeError("solo se analizan URLs http(s) del almacenamiento")
    args = [
        ffprobe_path,
        "-v",
        "error",
        "-protocol_whitelist",
        URL_PROTOCOLS,
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        url,
    ]
    code, stdout, stderr = await _run(args, timeout_s)
    if code != 0:
        raise ProbeError(f"ffprobe falló: {stderr.decode(errors='replace')[:500]}")
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ProbeError("ffprobe devolvió JSON inválido") from exc
    try:
        return parse_ffprobe_json(data)
    except ValueError as exc:
        raise ProbeError(str(exc)) from exc


async def ffprobe_version(ffprobe_path: str) -> str | None:
    try:
        code, stdout, _ = await _run([ffprobe_path, "-version"], timeout_s=10)
    except (OSError, ProbeError):
        return None
    if code != 0:
        return None
    match = re.search(r"ffprobe version (\S+)", stdout.decode(errors="replace"))
    return match.group(1) if match else None
