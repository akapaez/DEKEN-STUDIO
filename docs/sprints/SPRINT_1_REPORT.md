# Informe de Sprint 1 — Biblioteca audiovisual, marca DEKEN e integración de Remotion

Fecha: 2026-10-14 · Estado: **criterios S1-01 a S1-06 y de Remotion (S1-R1 a S1-R5)
cumplidos**, sin regresiones de Sprint 0, también en GitHub Actions
([CI run #3](https://github.com/akapaez/DEKEN-STUDIO/actions/runs/38570127121) backend ·
[CI run #4](https://github.com/akapaez/DEKEN-STUDIO/actions/runs/38575955545) completo).
Remotion queda integrado como motor principal
de composición **en modo evaluación**: los renders comerciales siguen deshabilitados hasta
que Grupo Deken verifique y regularice la licencia (ver §4).

Todas las pruebas se han ejecutado contra servicios reales (PostgreSQL 16, Valkey 8,
SeaweedFS, FFmpeg 6.1/7.1, Remotion 4.0.531 con Chrome Headless Shell), sin simulaciones.
Todo el material usado es **sintético** (barras, tono, colores planos y un glifo generado)
y está etiquetado como tal; no se ha usado ni inventado material de DEKEN.

## 1. Criterios de aceptación

| ID | Resultado | Evidencia |
|---|---|---|
| S1-01 Importación MP4/MOV | ✅ | `test_media_library.py`: MP4 vertical 1080×1920 con audio, MOV horizontal sin audio, MOV de móvil con rotación 90° (se ve 720×1280), subida multiparte real de 110 MB en 7 partes de 16 MiB. Errores: `.avi` → 422, 21 GiB → 413, parte que falta → 409 `upload_incomplete`. E2E: subida desde el navegador con progreso y cancelación. |
| S1-02 Ficheros falsos/corruptos | ✅ | Texto con extensión `.mp4` → `rejected` en la API (ffprobe) y objeto **borrado**; MP4 con cabeceras válidas y datos corruptos → `rejected` en la ingesta (decodificación de muestra, `invalid_media` sin reintentos). |
| S1-03 Originales intactos | ✅ | SHA-256 del original igual al del fichero subido tras toda la ingesta; el worker comprueba que no ha cambiado; la descarga desde la web es idéntica byte a byte (E2E). Archivar no borra el original. |
| S1-04 Miniaturas y proxy reales | ✅ | Vertical: póster 405×720, tira 1010×180 (10 fotogramas), proxy 540×960 H.264 + AAC decodificado entero, forma de onda; MOV rotado → proxy 540×960; horizontal sin audio → proxy 960×540 sin forma de onda. Todo verificado también en servidor. |
| S1-05 Biblioteca usable | ✅ | `apps/web/e2e/sprint1.spec.ts`: subida de un vídeo y un falso a la vez, estado por fichero, ficha con proxy (MP4 servido verificado con ffprobe; reproducción real en Chrome), forma de onda, catalogación, búsqueda, filtro por etiqueta y por estado, derechos de imagen (concedido sin referencia → error; con referencia → "Utilizable en piezas"), descarga del original; usuario de consulta sin acciones de escritura. |
| S1-06 Recursos de marca | ✅ | `test_brand.py` (6) + E2E: logo 5,2:1 → familia DEKEN, tinta medida `#76B82A`, fondo recomendado oscuro; fichero "…-BLANCO" que en realidad es gris → aviso "color distinto al del nombre" y fondo claro; logo de dos tintas → `verde-gris`; sin transparencia → aviso; fondo de uso editable y auditado; tipografía TTF analizada (familia, estilo, peso); JPEG como logo → 422; texto como PNG, PNG transparente o TTF falso → rechazados; el editor no gestiona la marca. |
| S1-R1 Prueba técnica de Remotion | ✅ | `test_remotion.py`: worker real → MP4 H.264 1080×1920 `yuv420p` 30/1 fps, **150 fotogramas exactos**, AAC, 5,0 s, decodificación completa; guardado en `evaluation/`, marca de agua, directorio del trabajo vacío. En CI, además, `deken-remotion-check` **dentro de la imagen del worker**. Fondo gris DEKEN, título animado, línea verde y barrido (revisado fotograma a fotograma). |
| S1-R2 Línea de tiempo | ✅ | Esquema inválido → 422 `invalid_timeline`; medio inexistente o en ingesta → 422 `unauthorized_media`; semántica inválida (texto < 2,5 s) → trabajo `failed` `invalid_timeline`, 1 intento, sin reintentos; vídeo 16:9 reencuadrado a 9:16 sin deformar → 90 fotogramas 1080×1920 con audio, verificado. |
| S1-R3 Licencia | ✅ | `purpose=production` → 409 `remotion_license_required` sin crear trabajo; el handler del worker y el renderer Node lo rechazan también (tests unitarios Python y vitest). |
| S1-R4 Fallos, cancelación y limpieza | ✅ | Cancelación a mitad de render (SIGTERM → `cancelSignal`) → `cancelled` sin salidas; motor no disponible → `engine_unavailable` reintentable; timeout y SIGKILL tras el periodo de gracia (`test_json_lines.py`); directorio del trabajo vacío tras éxito, fallo y cancelación. |
| S1-R5 Previsualización = render | ✅ | Remotion Player en *Configuración → Sistema* con la misma composición; el texto editado aparece en el Player; render lanzado desde la interfaz, verificado y descargado como `deken-evaluacion-remotion-*.mp4` (E2E). |
| Sin regresiones de Sprint 0 | ✅ | Los 125 tests de Sprint 0 siguen en verde (matriz de permisos ampliada con 16 rutas nuevas) y los 8 E2E de Sprint 0 también. |

## 2. Resultados de la verificación

```
uv run pytest (DEKEN_REQUIRE_REMOTION=1)   202 passed (0 omitidos)
pnpm -r test                               brand 5 · video-compositions 43 · remotion-renderer 13 · web 23
infra/scripts/e2e.sh                       14 passed (Sprint 0: 8 · Sprint 1: 6)
ruff · ruff format · mypy --strict         sin errores (68 ficheros)
tsc --strict (5 paquetes) · eslint         sin errores
check-generated · check-schema             OpenAPI, tipos TS y JSON Schema de la timeline al día
make check-secrets                         9 secretos buscados en 3.771 ficheros del build: ninguno aparece
deken-remotion-check                       ok: 1080×1920, 30 fps, 5 s, ~16 s por render
docker build web                           OK (local); worker: etapas Remotion y Python OK en local, imagen completa en CI
```

En GitHub Actions (Ubuntu 24.04, [run #4](https://github.com/akapaez/DEKEN-STUDIO/actions/runs/38575955545)),
los tres trabajos en verde:

- **Lint, tipos y unitarios**: ruff, mypy estricto, OpenAPI/tipos TS y JSON Schema de la
  timeline al día, `tsc` estricto en los 5 paquetes, ESLint y vitest.
- **Integración, render real y E2E**: `make remotion` (renderer, bundle, Chrome Headless
  Shell descargado por Remotion y render de evaluación verificado), pytest con
  `DEKEN_REQUIRE_REMOTION=1` (Remotion obligatorio, sin omitir tests), build web sin
  secretos, los 14 E2E con **Google Chrome** (reproducción real del proxy H.264) y copia de
  seguridad.
- **Imágenes Docker**: API, web y worker (dependencias de Chrome, Node, renderer, bundle y
  navegador) y `deken-remotion-check` **dentro de la imagen del worker**.

Tests nuevos por área: contrato compartido (14), unidades de la API para medios, marca,
esquema y permisos (28), biblioteca de integración (9), marca (6), Remotion de extremo a
extremo (7), operaciones FFmpeg de la ingesta (4), procesos con eventos JSON (4), handler
de Remotion (5); vitest de composiciones (43: esquema, semántica, geometría sin
deformación para 15 combinaciones de formato, plantillas, zonas seguras, movimiento),
renderer (13: licencia, especificación, servidor de entradas) y subida multiparte (6).

Incidencias detectadas y corregidas por las propias pruebas:

- Las salidas verificadas de la ingesta no llegaban al activo: la sesión no hace
  *autoflush* y el *hook* consultaba antes de volcar. Corregido con `flush` explícito.
- Póster y tira redondeaban el ancho a par (406 en vez de 405 px): en JPEG ya no hace
  falta; ahora son proporcionales exactos.
- `snap_fps(24)` devolvía 23,976 (primer estándar a < 0,5 %): ahora elige el más cercano.
- El JSON Schema generado no comprobaba que el tamaño correspondiera al formato (los
  `refine` de zod no se exportan): ahora es un literal por formato; la API comprueba
  además la duración máxima.
- Remotion descargaba Chrome en el directorio de cada trabajo (su caché depende del
  `cwd`): el navegador se instala una vez en el paquete del renderer y el worker lo
  localiza; sin navegador el motor se declara no disponible.
- El servidor local de entradas trataba mal `Range: bytes=-N` y rangos fuera del fichero:
  corregido (sufijo y 416).
- La imagen del worker no incluía los handlers de análisis y la de la web no incluía las
  composiciones: añadidos.
- En el render, un texto inferior y los subtítulos se solapaban (detectado revisando
  fotogramas reales): los subtítulos reservan ahora su banda inferior.
- El Remotion Player desbordaba su caja e interceptaba clics: dimensionado por ancho.
- El Chromium de Playwright no trae H.264: la prueba verifica el proxy servido con
  ffprobe y, en CI, la reproducción real con Google Chrome (`E2E_BROWSER_CHANNEL=chrome`).
- `e2e.sh` dejaba procesos huérfanos ocupando puertos: cada proceso va en su grupo.
- CORS del almacenamiento sin el origen de E2E y `operationId` duplicados entre biblioteca
  y marca: corregidos.

## 3. Arquitectura entregada

- **Biblioteca**: `media_assets` (migración `0002`), subida multiparte con `ListParts` en
  servidor, ffprobe en la API, `media.ingest` en `workers/analysis` y *hooks* de trabajo
  que actualizan el activo en la misma transacción. Interfaz `/biblioteca` y
  `/biblioteca/[id]`.
- **Marca**: `brand_assets`, análisis con Pillow y fontTools en la API, interfaz `/marca`.
- **Remotion** (ADR 0005): `packages/video-compositions` (esquema `deken.timeline/1`,
  reglas, geometría, composiciones, plantillas), `workers/render/remotion` (renderer
  Node), handlers Python, puerta de licencia triple, Player en la web, `make remotion`,
  `deken-remotion-check` e imagen del worker con el motor.
- Documentación: `ARCHITECTURE.md`, `IMPLEMENTATION_PLAN.md`, ADR 0005 (sustituye a la
  0004), `docs/DEPENDENCIES_AND_CREDENTIALS.md` (condición de licencia), `DATA_MODEL`,
  `CONTRACTS` (endpoints, tipos de trabajo y timeline), `SECURITY` (permisos y nuevas
  amenazas), guías de desarrollo y de worker WSL2.

## 4. Limitaciones y pendientes

**Licencia de Remotion (bloquea solo los renders comerciales)**

- Según la licencia de Remotion 4.0.531, el uso gratuito cubre personas, empresas de
  hasta 3 empleados, entidades sin ánimo de lucro y la **evaluación** sin uso comercial.
  Grupo Deken debe confirmar su encaje y, si procede, contratar la *Company License*.
- Hasta entonces: `DEKEN_REMOTION_LICENSE_MODE=evaluation`; producción rechazada en API,
  worker y renderer; renders con marca de agua en `evaluation/`. Activación documentada
  en la ADR 0005.
- En modo evaluación Remotion puede enviar un evento de uso anónimo a `remotion.pro`.

**Otras limitaciones conocidas**

- Aceptación con **material real de DEKEN** pendiente: no hay grabaciones, logos ni
  `.ttf` oficiales en la plataforma todavía (todo lo probado es sintético).
- En el entorno de desarrollo de esta sesión la red no permite `deb.debian.org` ni
  `remotion.media`: la imagen completa del worker (dependencias de Chrome y descarga del
  navegador) se ha verificado en GitHub Actions (run #4, en verde), no en local.
- La subida no se reanuda tras recargar la página: se aborta y se vuelve a subir.
- La forma de onda muestra niveles absolutos; la normalización de sonoridad llegará con
  el montaje (Sprint 3).
- Las tipografías subidas en *Marca* se analizan y catalogan, pero las composiciones usan
  las Montserrat e IBM Plex Mono empaquetadas (las mismas de la guía).
- El catálogo de 10 plantillas es estructura editable (datos); su uso para proponer
  montajes con planos reales es del Sprint 3. El editor completo es del Sprint 4.
- Cualquier usuario con `media:read` (todos los roles) puede descargar originales; la
  descarga queda auditada.

## 5. Dependencias para Sprints 2–4

1. Decisión de Grupo Deken sobre la licencia de empresa de Remotion.
2. Grabaciones reales, logos oficiales y tipografías en la plataforma (subida desde la web).
3. Criterio y referencias de consentimiento de las personas que aparecen.
4. Clave del proveedor de IA (opcional; sin ella, modo manual) y fuentes verificadas
   para la base de conocimiento (Sprint 2).

## 6. Endurecimiento posterior (preparación para material real)

Antes de la aceptación con material de DEKEN se probaron con equivalentes sintéticos los
casos reales de más riesgo. Hallazgos y correcciones:

| Caso | Hallazgo | Corrección y evidencia |
|---|---|---|
| Vídeo HDR de iPhone (HEVC 10 bits, HLG BT.2020, rotado) | El proxy salía lavado y sin saturación (PSNR 18 dB frente a la versión SDR de las mismas barras) y conservaba etiquetas BT.2020/HLG siendo de 8 bits | Mapeo de tono *mobius* a SDR BT.709 en póster, tira y proxy (27 dB); proxy etiquetado BT.709; la ficha muestra el rango dinámico. `test_hdr_proxy_is_tone_mapped_to_sdr`, `test_iphone_hdr_mov_gets_sdr_previews` |
| Render con Remotion de un original HDR | El mapeo de tono propio de Remotion también lo dejaba apagado (18,8 dB) | El worker crea una copia SDR del **tramo usado** antes de componer (27,6 dB) y desplaza los recortes; la línea de tiempo guardada no cambia. `test_hdr_source_is_tone_mapped_before_composing` (vídeo en movimiento desde el segundo 1, compara render HDR y SDR) y `test_source_windows.py` |
| Vídeos de más de 100 s | **Ninguno se podía ingerir**: el margen del 1 % superaba los topes del modelo `VideoSpec` (30 fotogramas, 5 s, 1 h) | Topes ampliados (duración máxima 6 h, rechazada con mensaje claro en la subida). Regresión cubierta para 100 s, 8 min, 2 h y 6 h |
| Mapeo de tono en 4K | 2,35 × la duración si se aplica antes de escalar | En el proxy se aplica tras escalar (0,57 ×, visualmente idéntico: 34 dB entre ambos); póster y tira lo aplican antes (zscale no admite anchos impares en 4:2:0) |

Medidas (4 vCPU): subida de 1,9 GB en 21 s y su ingesta (8 min de 1080p) en 104 s; render
Remotion de 60 s 1080×1920 con vídeo, textos y subtítulos en 295 s (1.800 fotogramas
exactos); la concurrencia de Remotion apenas mejora con 4 vCPU (−7 %).

La prueba de aceptación con material real queda descrita paso a paso en
[`docs/operations/ACEPTACION_MATERIAL_REAL.md`](../operations/ACEPTACION_MATERIAL_REAL.md).

