# Aceptación de Sprint 1 con material real de DEKEN

Sprint 1 está verificado con material **sintético**. Esta guía es la prueba de aceptación
con material **real** de Grupo Deken: qué subir, qué comprobar y qué anotar. Duración
estimada: 1–2 horas con un worker en marcha.

Requisitos: plataforma arrancada (`docs/deployment/LOCAL_DEV.md`), un worker conectado
con las colas `analysis` y `render` (en *Configuración → Workers* debe aparecer "En
línea") y un usuario administrador.

## 1. Qué subir (Biblioteca → Subir grabaciones)

Elige una muestra variada; no hace falta subirlo todo.

| # | Material | Por qué |
|---|---|---|
| V1 | Vídeo vertical de **iPhone reciente** (HDR, el ajuste por defecto) | HDR HLG/Dolby Vision en HEVC 10 bits, con rotación |
| V2 | Vídeo horizontal de móvil Android | Otro fabricante, posible cadencia variable |
| V3 | Clip **largo** (10 min o más) de un proceso de fábrica | Subida multiparte grande, ingesta larga |
| V4 | Clip de cámara (MOV, p. ej. ProRes o H.264 de cámara), si lo hay | Ficheros muy pesados, 4:2:2 |
| V5 | Clip en el que aparezcan **personas** | Flujo de derechos de imagen |
| V6 | El mismo fichero que V2, subido dos veces | Detección de duplicados |
| L1 | Logos oficiales de `Deken-Recursos/Versiones-Logo` (todas las variantes PNG) | Análisis de tinta, proporción y familia |
| F1 | `.ttf`/`.otf` oficiales de Montserrat, si DEKEN los tiene | Catálogo de tipografías |

## 2. Qué comprobar

### Biblioteca

- [ ] La subida muestra progreso y termina; cancelar a mitad deja el vídeo como cancelado.
- [ ] Cada vídeo pasa a **Lista**. Si alguno queda en *Rechazada* o *Error de proceso*,
      anota el motivo que muestra la ficha.
- [ ] **Colores (V1)**: en la ficha, "Rango dinámico" dice *HDR HLG* (o PQ) y el póster,
      la tira y el proxy **no** se ven lavados ni grises comparados con la Fototeca del
      iPhone. Ver §4 si se ven mal.
- [ ] Orientación correcta (V1 vertical sin girar ni deformar) y resolución coherente.
- [ ] Al pasar el ratón por la tarjeta se hojea la tira; el proxy se reproduce y la forma
      de onda sigue al reproductor.
- [ ] **V6** queda como *Duplicada* con enlace al original.
- [ ] **Descargar original** (V1 y V3) da exactamente el fichero subido (mismo tamaño;
      opcional: `sha256sum` antes y después).
- [ ] Etiquetas, búsqueda y filtros funcionan con los títulos reales.
- [ ] **V5**: un usuario *Revisión* marca "Aparecen personas", concede el consentimiento
      con su referencia y el vídeo pasa a "Utilizable en piezas"; queda en *Auditoría*.

### Marca DEKEN

- [ ] Cada logo muestra su familia (DEKEN, GD, GRUPO-DEKEN, GRUPO-DEKEN-HORIZONTAL) y la
      tinta medida.
- [ ] Los ficheros del kit cuyo nombre no coincide con su color (p. ej. los horizontales
      BLANCO y GRIS intercambiados) aparecen con el aviso **"Color distinto al del
      nombre"**. Corrige el color declarado o el fondo de uso desde la tarjeta.
- [ ] Ningún logo se ve deformado en las vistas previas sobre fondo claro y oscuro.

### Remotion (evaluación)

- [ ] *Configuración → Sistema → Remotion*: el worker aparece con Remotion y el render de
      evaluación termina con el MP4 verificado (1080×1920, 150 fotogramas).

## 3. Rendimiento de referencia (medido con material sintético, 4 vCPU)

| Operación | Medida |
|---|---|
| Subida de 1,9 GB (local) | 21 s |
| Ingesta de 8 min de 1080p (hash, póster, tira, proxy, forma de onda) | 104 s (≈ 0,22 × la duración) |
| Proxy de 4K HDR con mapeo de tono | ≈ 0,6 × la duración |
| Render Remotion de 60 s 1080×1920 (vídeo, textos, subtítulos) | 295 s (≈ 5 × la duración) |
| Copia SDR previa al render de un original 4K HDR (solo del tramo usado + 0,5 s) | ≈ 3,4 × la duración del tramo |

Un worker con más núcleos acorta los renders casi en proporción; la concurrencia de
Remotion apenas mejora con 4 vCPU.

## 4. Si algo falla

Anota para cada caso: fichero (nombre, móvil o cámara, tamaño, duración), estado y
motivo de la ficha, y una captura. Además:

- **Colores raros**: en la ficha, *Datos técnicos → Rango dinámico*. Si un vídeo HDR
  aparece como SDR, el móvil no etiquetó la curva de transferencia; envía el resultado de
  `ffprobe -v error -show_streams -of json fichero` (sin el vídeo).
- **Rechazado sin motivo claro**: *Configuración → Trabajos*, abre la ingesta y copia el
  error y su historial.
- **Muy lento**: anota la duración del vídeo y el tiempo de la ingesta (historial del
  trabajo).

Con esas notas se ajusta lo necesario antes de construir el montaje (Sprint 3).
