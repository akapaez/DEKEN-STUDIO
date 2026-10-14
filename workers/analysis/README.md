# workers/analysis — análisis de medios (Sprint 1 y 3)

**Estado: no implementado todavía.** Este directorio reserva el paquete de handlers de
análisis; ningún trabajo de análisis se ofrece en la interfaz hasta que exista y esté
probado.

Plan (ver `IMPLEMENTATION_PLAN.md` y `docs/CONTRACTS.md §3`):

| Tipo de trabajo | Sprint | Qué hará |
|---|---|---|
| `media.probe` | 1 | ffprobe del original + validación de contenido real (rechaza ficheros que no son vídeo) |
| `media.derive` | 1 | Póster, tira de miniaturas, proxy 540p H.264 y forma de onda |
| `media.segments` | 3 | Escenas, silencios, negros, congelados, desenfoque, nivel de audio y transcripción local (faster-whisper) |

Se apoyará en `workers/runtime` (`deken_worker`): mismo contrato, mismo sandbox de
procesos y registro de handlers por *entry point* `deken_worker.handlers`.
