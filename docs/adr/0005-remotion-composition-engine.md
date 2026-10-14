# ADR 0005 — Remotion como motor principal de composición; FFmpeg como motor auxiliar

- Estado: **aceptada** (Sprint 1). Sustituye a [ADR 0004](0004-ffmpeg-first-rendering.md).
- Condición vigente: **solo desarrollo y evaluación** hasta que Grupo Deken verifique y
  regularice la licencia de empresa de Remotion (ver §4).

## Contexto

La ADR 0004 dejaba FFmpeg (`filter_complex` generado) como motor de render de V1 y
Remotion como opción para piezas gráficas. La dirección del proyecto decide en Sprint 1
que la calidad de las piezas (títulos, transiciones, subtítulos dinámicos, marca,
plantillas, multicapa) y la necesidad de que **la previsualización y el render usen la
misma estructura** justifican un motor de composición declarativo como pieza central.

Requisitos que condicionan la decisión:

- Composiciones reutilizables con propiedades editables y estética de marca DEKEN.
- Una línea de tiempo JSON versionada y validada que interpreten igual el editor
  (Sprint 4), la previsualización en el navegador y el render del worker.
- Reglas audiovisuales: no deformar, conservar el aspecto, reencuadrar sin estirar,
  zonas seguras, subtítulos legibles, sincronía A/V, todo ajustable a mano.
- Licencia de Remotion: gratuita para personas, empresas de hasta 3 empleados,
  organizaciones sin ánimo de lucro y **evaluación** ("evaluating whether Remotion is a
  good fit, and are not yet using it in a commercial way"); el resto necesita *Company
  License* (texto en `node_modules/remotion/LICENSE.md`, versión 4.0.531).

## Decisión

1. **Remotion 4.0.531 es el motor principal de composición y render final**:
   composición, animaciones, motion graphics, títulos, transiciones, subtítulos
   dinámicos, logotipos, plantillas, multicapa y previsualización (Remotion Player).
2. **FFmpeg/ffprobe es el motor auxiliar**: análisis, metadatos, miniaturas, tiras,
   proxys, formas de onda, normalización, transcodificación, validación y verificación
   de salidas (en el worker y en el servidor).
3. **Interfaces desacopladas**:
   - `packages/video-compositions` (TS, sin dependencias del worker): esquema
     `deken.timeline/1` en zod (fuente única → JSON Schema generado para la API),
     reglas semánticas (`validate.ts`), geometría de reencuadre sin deformación,
     composiciones (`DekenEvaluation`, `DekenTimeline`) y catálogo de 10 plantillas.
   - `workers/render/remotion` (Node): renderer que recibe una *especificación de
     render* con **rutas locales** del directorio del trabajo; emite eventos JSON por
     líneas (progreso, fin, error) y atiende SIGTERM como cancelación.
   - `workers/render` (Python): handlers `system.remotion_eval` y `render.timeline`
     sobre el contrato de trabajos v1 (descarga verificada de entradas, progreso,
     cancelación, reintentos, subida y verificación local con ffprobe +
     decodificación completa). La API vuelve a verificar la salida en servidor.
4. **Ningún secreto llega a las composiciones**: la API resuelve los medios
   autorizados y entrega al worker URLs firmadas de lectura; el worker los descarga y la
   composición solo ve URLs de un servidor local (127.0.0.1, ruta con token aleatorio,
   confinado al directorio del trabajo). Las claves de almacenamiento solo existen en la
   API; la línea de tiempo guarda IDs, nunca URLs.
5. **Puerta de licencia** (`DEKEN_REMOTION_LICENSE_MODE`, por defecto `evaluation`),
   aplicada en tres puntos independientes:
   - API: `purpose=production` → 409 `remotion_license_required` salvo modo `company`.
   - Worker Python: rechaza `production` si su modo no es `company`.
   - Renderer Node: `licenseFor()` exige modo `company` **y** clave para producción.
   En modo evaluación los renders llevan marca de agua ("Evaluación técnica · no
   publicar"), se guardan en el prefijo `evaluation/` (tipo de objeto `evaluation`) y se
   descargan como `deken-evaluacion-remotion-*.mp4`, separados del contenido comercial.

## Consecuencias

- La previsualización (Player en la web) y el render (worker) ejecutan **el mismo
  código** de `@deken/video-compositions`; las tipografías de marca se cargan con una
  comprobación estricta en el render (`document.fonts.check`, se cancela si fallan).
- El worker necesita Node 22, el renderer compilado, el bundle de composiciones y
  Chrome Headless Shell (incluidos en `infra/docker/worker.Dockerfile`;
  `make remotion` en desarrollo; `deken-remotion-check` comprueba la máquina).
- Mientras la licencia no se regularice: **no hay renders comerciales**. El editor
  (Sprint 4) y los montajes automáticos (Sprint 3) se desarrollan sobre la arquitectura
  ya validada, renderizando solo en modo evaluación.
- En modo evaluación Remotion usa `licenseKey: "free-license"` y puede enviar un evento
  de uso anónimo a `remotion.pro` (sin contenido de vídeo). Si falla la conexión el
  render continúa. Con licencia de empresa se usará la clave contratada.
- El render con FFmpeg de la ADR 0004 no se implementa; FFmpeg sigue siendo
  imprescindible para ingesta y verificación.

## Activación de renders comerciales (cuando proceda)

1. Grupo Deken contrata la *Company License* en remotion.pro y conserva la factura.
2. Responsable técnico registra la referencia en
   [`docs/DEPENDENCIES_AND_CREDENTIALS.md`](../DEPENDENCIES_AND_CREDENTIALS.md).
3. Se configura `DEKEN_REMOTION_LICENSE_MODE=company` en API y workers, y
   `DEKEN_REMOTION_LICENSE_KEY` **solo en los workers** (variable o `/run/secrets`).
4. Se verifica en *Configuración → Sistema* que el motor indica "Licencia de empresa".
