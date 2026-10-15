"""Color de vídeo: HDR (HLG/PQ, típico de móviles) → SDR BT.709.

Lo usan la ingesta (póster, tira, proxy) y el render (copia intermedia SDR del original
antes de componer con Remotion, cuyo mapeo de tono propio deja el HDR apagado). Mapeo
*mobius*: conserva casi intactos los colores dentro de rango y comprime las altas luces.
"""

from __future__ import annotations

from pathlib import Path

from deken_worker.process import file_input

TONE_MAP_TO_SDR = (
    "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
    "tonemap=tonemap=mobius:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
)
BT709_TAGS = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]


def sdr_prefix(hdr: bool) -> str:
    """Prefijo de cadena de filtros: mapeo de tono si la fuente es HDR."""
    return f"{TONE_MAP_TO_SDR}," if hdr else ""


def sdr_mezzanine_args(
    source: Path,
    out: str,
    *,
    has_audio: bool,
    start_s: float = 0.0,
    length_s: float | None = None,
) -> list[str]:
    """Copia intermedia SDR de alta calidad (H.264 CRF 14) con el audio original intacto.

    `start_s`/`length_s`: solo el tramo que se usa (búsqueda precisa: se recodifica).
    Contenedor MOV para admitir cualquier audio de origen sin recodificar."""
    audio = ["-map", "0:a:0?", "-c:a", "copy"] if has_audio else ["-an"]
    window = ["-ss", f"{start_s:.3f}"] if start_s > 0 else []
    length = ["-t", f"{length_s:.3f}"] if length_s else []
    return [
        *window, *file_input(source), *length,
        "-map", "0:v:0", *audio,
        "-vf", TONE_MAP_TO_SDR,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p",
        *BT709_TAGS,
        "-metadata", "comment=DEKEN STUDIO AI - copia SDR para componer (no es el original)",
        out,
    ]  # fmt: skip
