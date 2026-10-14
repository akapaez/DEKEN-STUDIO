# workers/analysis — análisis de medios con FFmpeg

Paquete `deken-analysis`: handlers de la cola `analysis`, registrados por el *entry
point* `deken_worker.handlers` (`analysis`). Usa `workers/runtime` (`deken_worker`):
mismo contrato de trabajos v1, mismo sandbox de procesos (listas de argumentos,
`-protocol_whitelist`, rutas confinadas, timeouts y cancelación).

| Tipo de trabajo | Sprint | Estado |
|---|---|---|
| `media.ingest` | 1 | **Implementado y probado** |
| `media.segments` | 3 | Pendiente: escenas, silencios, negros, congelados, desenfoque, nivel de audio y transcripción local (faster-whisper) |

## `media.ingest`

La API lo encola al cerrar una subida que ya pasó ffprobe en el servidor.

1. Descarga del original con URL firmada y comprobación de tamaño y **SHA-256**.
2. ffprobe local y **decodificación de muestra** (`-xerror`, primeros segundos): un fichero
   con cabeceras válidas pero datos corruptos falla con `invalid_media` (no reintentable)
   y el activo queda `rejected`.
3. Derivados (FFmpeg aplica la rotación del móvil; nunca se deforma, `setsar=1`):
   - `poster`: JPEG, lado mayor ≤ 720 px, sin ampliar.
   - `strip`: tira de 10 fotogramas, 180 px de alto (para hojear en la galería).
   - `proxy`: MP4 H.264 High `yuv420p` + AAC, lado corto 540 px, cadencia ajustada al
     estándar más próximo, `+faststart`; se verifica localmente (`check_video_spec`).
   - `waveform`: JSON con 1000 picos absolutos (0–1) desde PCM 8 kHz en *streaming*
     (solo si hay audio; salida opcional).
4. Se comprueba que el original **no ha cambiado** (mismo SHA-256) y se suben las salidas;
   la API las verifica en servidor y actualiza el activo (`ready`, `duplicate` si el hash
   coincide con otro activo listo).

Pruebas: `workers/analysis/tests/test_ffmpeg_ops.py` (señales sintéticas) e
integración de extremo a extremo en `services/api/tests/integration/test_media_library.py`.
