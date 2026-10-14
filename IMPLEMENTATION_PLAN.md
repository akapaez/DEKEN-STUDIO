# DEKEN STUDIO AI — Plan de implementación

Cada sprint tiene criterios de aceptación **verificables** (un comando, un test o una
comprobación manual concreta). Un sprint no empieza hasta que el anterior cumple los
suyos. Las funciones de V2 no se empiezan hasta cerrar V1.

Estado actual: **Sprints 0 y 1 implementados y verificados**, con Remotion integrado
como motor principal de composición en modo **evaluación** (licencia de empresa
pendiente) — ver [docs/sprints/SPRINT_0_REPORT.md](docs/sprints/SPRINT_0_REPORT.md) y
[docs/sprints/SPRINT_1_REPORT.md](docs/sprints/SPRINT_1_REPORT.md).

> **Decisión de Sprint 1** ([ADR 0005](docs/adr/0005-remotion-composition-engine.md)):
> Remotion es el motor principal de composición, animación y render final; FFmpeg queda
> para análisis, proxys, normalización y verificación. Hasta regularizar la licencia de
> Remotion solo se renderiza en modo evaluación; esto **no bloquea** el resto de sprints.

## Definición de "hecho" (todos los sprints)

1. Código con tipado estricto (mypy `--strict`, `tsc --strict`) y lint limpio (ruff, eslint).
2. Tests unitarios y de integración del sprint en verde en CI.
3. Migraciones versionadas, reversibles (`upgrade` / `downgrade`) y sin deriva (`alembic check`).
4. OpenAPI regenerada y tipos TS sincronizados (CI lo comprueba).
5. Documentación de operación actualizada.
6. Ninguna función se muestra como operativa si no lo es.
7. Ningún dato ficticio fuera de tests etiquetados como sintéticos.

## Recorrido fundamental (criterio de producto V1)

DEKEN STUDIO AI es funcional cuando un usuario puede, con vídeos reales:

| Paso | Sprint | Verificación automática |
|---|---|---|
| Importar vídeos | 1 ✅ | `apps/web/e2e/sprint1.spec.ts` + integración `test_media_library.py` |
| Crear un proyecto | 3 | journey paso 2 |
| Generar o escribir un guion | 2 | journey paso 3 (modo manual siempre; IA si está configurada) |
| Obtener una propuesta de montaje | 3 | journey paso 4 |
| Modificar planos y textos | 4 | journey paso 5 |
| Renderizar | 3/4 (motor ✅ en 1) | journey paso 6 + `test_remotion.py` (render Remotion real verificado) |
| Descargar y reproducir el MP4 | 3 | journey paso 7: ffprobe del fichero descargado (1080×1920, 30 fps, H.264/AAC, duración ±1 frame) |
| Guardar y recuperar el proyecto | 3/4 | journey paso 8: recarga, re-render idéntico en estructura |

El test de recorrido se ejecuta en CI con clips **sintéticos etiquetados**
(`tests/fixtures/synthetic/`) y, en la máquina de producción, con un vídeo real de
DEKEN como prueba de aceptación manual documentada.

---

## Sprint 0 — Infraestructura, base de datos, almacenamiento y autenticación

**Alcance**
- Monorepo (uv + pnpm), CI, Docker Compose (PostgreSQL, Redis, SeaweedFS).
- API FastAPI v1: configuración por entorno/ficheros de secretos, logging estructurado,
  salud, estado del sistema.
- Modelo de datos base y migración 0001: usuarios, sesiones, auditoría, workers,
  trabajos, eventos de trabajo, objetos almacenados, salidas de trabajo.
- Autenticación por sesión, CSRF, roles y permisos, limitación de intentos, auditoría.
- Almacenamiento S3 con URLs firmadas y claves generadas por servidor.
- Contrato de trabajos v1 completo (claim, lease, progreso, salidas, completado con
  verificación, fallo, reintentos, cancelación) y SDK de worker.
- Autotest de render: un worker real genera una señal sintética 1080×1920 H.264/AAC,
  la sube y la API la verifica con ffprobe. Es una **prueba técnica etiquetada**, no
  contenido.
- Web: login, layout con navegación lateral (secciones futuras deshabilitadas),
  tema claro/oscuro, Dashboard con estado real, Configuración (sistema, usuarios,
  workers, trabajos, auditoría).
- Scripts de backup/restauración.

**Criterios de aceptación**

| ID | Criterio | Verificación |
|---|---|---|
| S0-01 | Servicios de infraestructura arrancan sanos | `make services-up` → `docker compose ps` muestra postgres, redis (Valkey) y seaweedfs `healthy` |
| S0-02 | Migraciones reversibles y sin deriva | `services/api/tests/migrations/test_migrations.py` (upgrade → downgrade → upgrade; `alembic check`) |
| S0-03 | Salud y disponibilidad | `GET /api/v1/health/ready` → 200 con `database`, `redis`, `storage` = `ok`; 503 si caen BD o almacenamiento; `degraded` (200) si solo cae Redis, que tiene alternativa (test) |
| S0-04 | Autenticación | tests: login correcto/incorrecto, sesión caducada, logout revoca, usuario desactivado pierde acceso inmediatamente |
| S0-05 | Roles y permisos | tests de matriz: cada ruta protegida devuelve 403 al rol sin permiso |
| S0-06 | CSRF y origen | tests: POST con cookie sin `X-CSRF-Token` → 403; `Origin` ajeno → 403 |
| S0-07 | Limitación de login | test: el intento 11 en la ventana devuelve 429 |
| S0-08 | Auditoría | tests: login OK/KO, alta de usuario, cambio de rol, alta/revocación de worker generan eventos |
| S0-09 | Storage | tests: bucket creado, URL firmada de subida/descarga funcional y caducada tras expirar; claves no derivadas de entrada de usuario |
| S0-10 | Contrato de trabajos | tests: claim exclusivo concurrente, progreso renueva lease, lease expirado reencola, reintentos con backoff hasta `max_attempts`, cancelación en cola y en curso, fallo de verificación → `failed` |
| S0-11 | Render real verificado | `services/api/tests/integration/test_render_selftest.py`: worker real + FFmpeg → MP4 1080×1920, 30 fps, H.264 + AAC, duración pedida; la API lo verifica y queda `completed` |
| S0-12 | Web | Playwright `apps/web/e2e/sprint0.spec.ts`: login, dashboard con estado real, alta de usuario, registro de worker, autotest completado y MP4 descargable, logout; tema claro/oscuro |
| S0-13 | Secretos fuera del frontend | `make check-secrets`: el build de `apps/web` no contiene ningún valor de secreto del `.env` |
| S0-14 | Backup | `infra/scripts/backup.sh` genera dump + réplica de objetos; restauración en BD vacía verificada (`docs/operations/BACKUP_RESTORE.md`) |
| S0-15 | Calidad | CI: ruff, mypy strict, pytest, tsc, eslint, vitest, playwright en verde |

**Dependencias externas**: ninguna (todo local).

---

## Sprint 1 — Biblioteca audiovisual, identidad corporativa e integración de Remotion ✅

**Alcance (implementado)**
- Importación MP4/MOV por **subida multiparte** directa al almacenamiento (URLs firmadas
  por parte, cancelación, reintentos), validación en la API (`ListParts` + ffprobe),
  originales inmutables, SHA-256 y **duplicados**.
- Trabajo `media.ingest` (FFmpeg, cola `analysis`): decodificación de muestra (detecta
  corruptos), póster, tira, proxy 540p sin deformar (rotación y SAR), forma de onda.
- Biblioteca: galería con póster y tira para hojear, búsqueda, filtros (estado,
  orientación, audio, consentimiento), etiquetas, ficha con reproductor del proxy y forma
  de onda sincronizada, metadatos técnicos, catalogación, **derechos de imagen**
  (personas, consentimiento con referencia, restricciones, titular; auditados) y descarga
  del original; archivado sin borrar.
- Marca DEKEN: paleta y reglas, logos analizados de verdad (proporción y familia, tinta
  medida frente al nombre del fichero, transparencia, fondo recomendado y de uso, vista
  previa sobre fondo claro y oscuro), tipografías (fontTools) e imágenes corporativas.
- **Remotion** (ADR 0005): `packages/video-compositions` (línea de tiempo
  `deken.timeline/1` en zod → JSON Schema para la API, reglas semánticas, geometría sin
  deformación, composiciones de evaluación y de línea de tiempo, catálogo de 10
  plantillas), renderer Node en `workers/render/remotion`, handlers
  `system.remotion_eval` y `render.timeline`, puerta de licencia triple, previsualización
  con Remotion Player en *Configuración → Sistema*, imagen del worker con el motor.
- **No incluido** (por decisión de alcance): editor completo (Sprint 4) y montajes
  automáticos (Sprint 3). La arquitectura de ambos queda preparada y validada.

**Criterios de aceptación**

| ID | Criterio | Verificación | Estado |
|---|---|---|---|
| S1-01 | Importar MP4 y MOV (por defecto hasta 20 GiB), multiparte real | `test_media_library.py`: MP4 vertical con audio, MOV horizontal sin audio, MOV con rotación de móvil, subida > 100 MB en ≥ 7 partes; parte que falta → 409; > 20 GiB → 413; `.avi` → 422 | ✅ |
| S1-02 | Rechazo de ficheros falsos/corruptos | texto con extensión `.mp4` → `rejected` y objeto borrado; MP4 con datos corruptos → `rejected` en la ingesta | ✅ |
| S1-03 | Originales intactos | SHA-256 del original igual al subido tras todo el procesado; descarga desde la web idéntica byte a byte (E2E) | ✅ |
| S1-04 | Miniaturas y proxy reales | póster 405×720, tira 1010×180, proxy 540×960 H.264 + AAC decodificado entero, forma de onda; MOV rotado → proxy vertical | ✅ |
| S1-05 | Biblioteca usable | `sprint1.spec.ts`: subir desde el navegador con progreso, ficha con proxy y forma de onda, catalogar, buscar y filtrar por etiqueta, derechos de imagen, descarga; usuario de consulta sin acciones de escritura | ✅ |
| S1-06 | Recursos de marca | `test_brand.py` + `sprint1.spec.ts`: proporción y familia calculadas, tinta medida, aviso cuando el nombre no coincide, fondo de uso por variante, tipografías, rechazos | ✅ |
| S1-R1 | Prueba técnica de Remotion | `test_remotion.py`: 5 s, 1080×1920, 30 fps, 150 fotogramas exactos, H.264 `yuv420p` + AAC, decodificación completa, guardado en `evaluation/`; también dentro de la imagen del worker (`deken-remotion-check` en CI) | ✅ |
| S1-R2 | Línea de tiempo validada y renderizada | esquema (422), medios no autorizados (422), semántica inválida → `invalid_timeline` sin reintentos, reencuadre 16:9 → 9:16 sin deformar renderizado y verificado | ✅ |
| S1-R3 | Puerta de licencia | producción → 409 en la API; rechazo en worker y renderer (tests unitarios) | ✅ |
| S1-R4 | Cancelación y limpieza | cancelación a mitad de render detiene Remotion; directorio del trabajo vacío tras éxito, fallo y cancelación | ✅ |
| S1-R5 | Previsualización = render | Remotion Player en la web con la misma composición; render lanzado desde la interfaz y verificado con ffprobe (E2E) | ✅ |

**Dependencias**: material real de DEKEN (`Deken-Recursos/Videos-bruto`, logos,
`.ttf`) para la aceptación manual; licencia de empresa de Remotion para renders
comerciales (pendiente, no bloquea).

---

## Sprint 2 — Director creativo, guiones y calendario

**Alcance**
- Base de conocimiento: fuentes verificadas y hechos aprobados.
- Proveedor IA configurable (servidor). Generación de estrategias, campañas, ideas,
  guiones, storyboards temporizados, narraciones, títulos, descripciones, CTA y
  propuestas de grabación, con citas a hechos.
- Modo manual completo sin IA.
- Contenido con objetivo, público, plataforma, formato, duración, mensaje, CTA y
  estado de aprobación; flujo de aprobación con roles.
- Calendario editorial (mes/semana) y campañas.

**Criterios de aceptación**

| ID | Criterio | Verificación |
|---|---|---|
| S2-01 | Sin IA configurada la interfaz lo indica y todo funciona en manual | Playwright con `AI_PROVIDER` vacío |
| S2-02 | Cifras/afirmaciones técnicas sin cita se bloquean | test unitario del validador de grounding |
| S2-03 | Contrato de proveedor IA | tests con proveedor de prueba (etiquetado) + test de contrato opcional contra API real con clave |
| S2-04 | Flujo de aprobación | tests: `editor` no puede aprobar; `reviewer` sí; historial auditado |
| S2-05 | Calendario | Playwright: crear campaña, programar contenido, mover fecha, filtrar por plataforma |

**Dependencias**: clave de API del proveedor IA (opcional); fuentes documentales verificadas por DEKEN.

---

## Sprint 3 — Montaje automático y exportación real

**Alcance**
- Trabajo `media.segments`: escenas, silencios, negros, congelados, desenfoque,
  nivel de audio; transcripción local (faster-whisper).
- Clasificación de segmentos (manual + IA opcional con miniaturas).
- Proyectos y timeline v1 versionada.
- Propuesta de montaje a partir de guion/storyboard + segmentos disponibles (sin
  inventar escenas: si falta un plano, la propuesta lo marca como "pendiente de
  grabar").
- Propuesta de montaje como documento `deken.timeline/1` (ya validado por la API) y
  render `render.timeline` con **Remotion** (motor ya integrado) y verificación de
  salida; renders comerciales solo con licencia de empresa de Remotion.

**Criterios de aceptación**

| ID | Criterio | Verificación |
|---|---|---|
| S3-01 | Segmentos detectados reproducibles | test con clip sintético de cortes conocidos (tolerancia ±2 frames) |
| S3-02 | Propuesta sin escenas inventadas | test: todo clip de la propuesta referencia un segmento existente |
| S3-03 | Render real | `test_render_real.py`: 1080×1920, 30 fps, H.264 High yuv420p, AAC 48 kHz, duración configurada ±1 frame, sincronía A/V (desfase < 1 frame), decodificación completa sin errores |
| S3-04 | Sin deformación | test: clip 16:9 y 4:3 → píxel de aspecto 1:1 y SAR 1:1 en la salida |
| S3-05 | Re-render | test: guardar, recargar y volver a renderizar produce salida válida |

---

## Sprint 4 — Editor, reencuadre, subtítulos y ajustes

**Alcance**: editor de timeline sobre `deken.timeline/1` (mover, recortar, dividir,
reordenar, pistas de texto, subtítulos, marca y audio), previsualización con **Remotion
Player** (misma composición que el render), reencuadre manual sin deformar (las reglas
de `validate.ts` se aplican mientras se edita), subtítulos desde transcripción editables
en zonas seguras, volumen y fundidos, historial de versiones y deshacer.

**Criterios de aceptación**

| ID | Criterio | Verificación |
|---|---|---|
| S4-01 | Edición persistente | Playwright: editar, recargar, cambios presentes |
| S4-02 | Reencuadre respetado en render | test: rectángulo de recorte → contenido esperado en fotograma de salida (comparación por regiones) |
| S4-03 | Subtítulos legibles | test: tamaño ≥ 30 px a 1080×1920, dentro de zona segura, contraste con caja |
| S4-04 | Recorrido fundamental completo | `e2e/journey.spec.ts` en verde |

---

## Sprint 5 — Pruebas, seguridad, recuperación y estabilización

**Alcance**: revisión de seguridad (OWASP ASVS L2 como guía), pruebas de carga
ligeras (10 usuarios, 3 renders simultáneos), simulacro de restauración completa,
recuperación ante caídas (worker, Redis, storage), documentación de usuario y de
operación, accesibilidad (WCAG 2.1 AA en las secciones V1).

**Criterios de aceptación**: simulacro de restauración documentado con tiempos;
caída de worker a mitad de render → reintento correcto; auditoría de accesibilidad
sin bloqueantes; `security-review` sin hallazgos altos abiertos.

---

## Fuera de V1 (V2)

Publicación programada vía APIs oficiales con OAuth (Meta, LinkedIn, YouTube,
TikTok), gestión de cuentas sociales, estadísticas importadas, registro de leads,
informes periódicos, workers en la nube con GPU. Las secciones *Publicaciones* y
*Analítica y leads* aparecen deshabilitadas en la navegación.
