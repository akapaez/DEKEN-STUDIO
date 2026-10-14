# DEKEN STUDIO AI — Plan de implementación

Cada sprint tiene criterios de aceptación **verificables** (un comando, un test o una
comprobación manual concreta). Un sprint no empieza hasta que el anterior cumple los
suyos. Las funciones de V2 no se empiezan hasta cerrar V1.

Estado actual: **Sprint 0 implementado y verificado** — ver
[docs/sprints/SPRINT_0_REPORT.md](docs/sprints/SPRINT_0_REPORT.md).

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
| Importar vídeos | 1 | `tests/e2e/journey.spec.ts` paso 1 + integración `test_media_import.py` |
| Crear un proyecto | 3 | journey paso 2 |
| Generar o escribir un guion | 2 | journey paso 3 (modo manual siempre; IA si está configurada) |
| Obtener una propuesta de montaje | 3 | journey paso 4 |
| Modificar planos y textos | 4 | journey paso 5 |
| Renderizar | 3/4 | journey paso 6 + `test_render_real.py` |
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

## Sprint 1 — Biblioteca audiovisual e identidad corporativa

**Alcance**
- Importación MP4/MOV por subida multiparte con URL firmada; límites de tamaño y
  tipo; SHA-256; detección de duplicados.
- Trabajo `media.probe`: validación de contenido real con ffprobe (rechaza ficheros
  que no son vídeo aunque tengan extensión válida).
- Trabajo `media.derive`: miniaturas (póster + tira), proxy 540p H.264 para
  previsualización, forma de onda.
- Biblioteca: listado, filtros, etiquetas manuales, ficha del activo con
  reproducción del proxy, metadatos técnicos, consentimiento de personas grabadas,
  origen (siempre material real de DEKEN).
- Marca DEKEN: subida de logos oficiales y tipografías, paleta y reglas
  (desde `packages/brand`), validación de proporciones de logo.

**Criterios de aceptación**

| ID | Criterio | Verificación |
|---|---|---|
| S1-01 | Importar MP4 y MOV hasta el límite configurado (por defecto 20 GB) | integración con ficheros sintéticos de 3 tamaños; multiparte > 100 MB |
| S1-02 | Rechazo de ficheros falsos/corruptos | test: `.mp4` que es texto → rechazado con motivo |
| S1-03 | Originales intactos | test: SHA-256 del original igual antes y después de todo el procesado |
| S1-04 | Miniaturas y proxy reales | test: existen, dimensiones correctas, proxy reproducible (ffprobe + decodificación completa) |
| S1-05 | Biblioteca usable | Playwright: subir, ver progreso, ver miniatura y reproducir proxy, etiquetar, buscar |
| S1-06 | Recursos de marca | Playwright: subir logo, ver proporción calculada, marcar variante por fondo |

**Dependencias**: material real de DEKEN (`Deken-Recursos/Videos-bruto`, logos, `.ttf`).

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
- Render `render.timeline` con FFmpeg y verificación de salida.

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

**Alcance**: editor de timeline (mover, recortar, dividir, reordenar, pistas de
texto y audio), reencuadre manual con vista previa real (fotograma del proxy),
subtítulos desde transcripción editables en zonas seguras, ajustes de volumen y
fundidos, historial de versiones y deshacer.

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
