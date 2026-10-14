# packages/shared

Contratos compartidos entre la API, los workers y la web.

| Ruta | Contenido |
|---|---|
| `python/` (`deken-shared`) | Contrato de trabajos v1 (`jobs.py`) y verificación de vídeo (`media.py`). Fuente única para API y workers. |
| `openapi/openapi.json` | Esquema OpenAPI exportado de la API (generado, versionado). |
| `ts/` (`@deken/shared`) | Tipos TypeScript generados del OpenAPI + etiquetas en español. |

Regenerar tras cambiar la API: `pnpm generate:api`. CI ejecuta `check-generated`.
