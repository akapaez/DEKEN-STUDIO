# Dependencias externas y credenciales

Ninguna credencial se guarda en el repositorio ni llega al navegador. En desarrollo
se leen de `infra/.env` (copiado de `infra/.env.example`); en producción, de
variables de entorno o de ficheros en `/run/secrets/<nombre>` (Docker secrets). La
API acepta cualquier variable `X` también como fichero `X_FILE`.

## 1. Credenciales del sistema (Sprint 0)

| Variable | Quién la necesita | Cómo se genera | Rotación |
|---|---|---|---|
| `DEKEN_SECRET_KEY` | API | `openssl rand -base64 48` (≥ 32 bytes) | Rotarla invalida los tokens CSRF; las sesiones se mantienen (están en BD). |
| `DEKEN_DATABASE_URL` (o `POSTGRES_*`) | API, migraciones | Usuario dedicado `deken` con permisos solo sobre su BD | Anual o ante incidente |
| `DEKEN_REDIS_URL` | API | Con contraseña (`requirepass`) en producción | — |
| `DEKEN_S3_ACCESS_KEY` / `DEKEN_S3_SECRET_KEY` | **Solo API** | Usuario S3 con acceso únicamente al bucket de la plataforma | Anual |
| `DEKEN_WORKER_TOKEN` | Cada worker | Lo emite un admin en *Configuración → Workers* (se muestra una sola vez) | Revocable al instante desde la interfaz |
| Contraseña del admin inicial | Persona responsable | `deken-api create-admin` (pide la contraseña por teclado) | El usuario la cambia desde la interfaz |

Los workers **no** tienen credenciales de BD, Redis ni S3: solo su token de worker.

### 1.1 Remotion (Sprint 1)

| Variable | Quién la necesita | Valor | Notas |
|---|---|---|---|
| `DEKEN_REMOTION_LICENSE_MODE` | API y workers | `evaluation` (por defecto) o `company` | Con `evaluation` la API rechaza renders de producción (409 `remotion_license_required`). |
| `DEKEN_REMOTION_LICENSE_KEY` | **Solo workers** | Clave de la *Company License* | Nunca en la API, la web ni las composiciones. Fichero de especificación de render con permisos 600 y borrado al terminar. |
| `DEKEN_REMOTION_BROWSER` | Workers (opcional) | Ruta a Chrome Headless Shell | Por defecto, el que instala `make remotion` (o el de la imagen del worker). |

## 1.2 Condición de licencia de Remotion — **vigente**

> **Durante esta fase, el uso de Remotion se limita a desarrollo y evaluación
> autorizados por su licencia. No se habilitan renders comerciales mediante Remotion
> hasta verificar y regularizar la licencia correspondiente.**
> Decisión registrada en [ADR 0005](adr/0005-remotion-composition-engine.md).

- **Qué dice la licencia** (Remotion 4.0.531, `LICENSE.md` del paquete): uso gratuito
  para personas, empresas con ánimo de lucro de **hasta 3 empleados**, entidades sin
  ánimo de lucro y para **evaluar** si Remotion encaja "sin usarlo todavía de forma
  comercial". Las demás empresas necesitan *Company License* (remotion.pro).
- **Situación de Grupo Deken**: pendiente de que la empresa confirme su encaje y, si
  procede, contrate la *Company License*. Hasta entonces la plataforma opera en modo
  `evaluation`.
- **Cómo lo garantiza el sistema** (tres comprobaciones independientes): la API no crea
  renders de producción, el worker los rechaza y el renderer exige modo `company` más
  clave. Los renders de evaluación llevan marca de agua "Evaluación técnica · no
  publicar", se guardan en `evaluation/` y se descargan como
  `deken-evaluacion-remotion-*.mp4`. La previsualización (Remotion Player) solo se usa
  en el panel técnico de *Configuración → Sistema*.
- **Telemetría**: en modo evaluación Remotion usa `licenseKey: "free-license"` y puede
  enviar un evento de uso anónimo a `remotion.pro` (sin contenido). Si la red lo bloquea,
  el render continúa.
- **No bloquea el resto**: biblioteca, ingesta (FFmpeg), marca, guiones y calendario no
  dependen de Remotion.
- **Para activar renders comerciales**: ver "Activación" en la ADR 0005.

## 2. Dependencias externas por sprint

| Sprint | Dependencia | Necesaria para | Quién la aporta | Estado |
|---|---|---|---|---|
| 0 | Ninguna | — | — | ✅ |
| 1 | Grabaciones reales (`Deken-Recursos/Videos-bruto`) | Aceptación manual de importación | DEKEN | Pendiente de recibir en el servidor |
| 1 | Logos oficiales (`Deken-Recursos/Versiones-Logo`) y `.ttf` de Montserrat | Marca DEKEN (la sección ya analiza los ficheros al subirlos) | DEKEN | Pendiente de subir a la plataforma |
| 1 | Consentimientos de imagen de personas que aparecen en grabaciones | Uso de esos planos | DEKEN (RR. HH./legal) | Pendiente |
| 2 | Clave API del proveedor IA (`DEKEN_AI_PROVIDER`, `DEKEN_AI_API_KEY`, `DEKEN_AI_MODEL`) | Director IA (opcional: sin ella, modo manual) | DEKEN contrata la cuenta | Pendiente |
| 2 | Fuentes verificadas: fichas técnicas Schüco de los sistemas que DEKEN fabrica, certificados reales, catálogo propio | Base de conocimiento | DEKEN (dirección técnica) | Pendiente |
| 3 | Modelo Whisper (descarga única, ~1,5 GB `large-v3` o ~150 MB `small`) | Transcripción local | Descarga automática en el worker | — |
| 3/4 | Biblioteca musical con licencia (o ninguna) | Música en renders | DEKEN | Pendiente; sin ella los renders van sin música |
| 1 | Licencia Remotion *Company License* | Renders comerciales con el motor de composición (Remotion) | DEKEN | **Pendiente de verificar/regularizar** → solo evaluación (marca de agua, `evaluation/`) |
| 1 | Acceso de los workers a `remotion.media` (descarga de Chrome Headless Shell al construir la imagen) | Imagen del worker | Red del entorno de build | Disponible en CI; en redes restringidas usar `DEKEN_REMOTION_BROWSER` |
| Producción | Dominio + certificado TLS, servidor (≥ 4 vCPU, 8 GB, almacenamiento para vídeo) | Despliegue | DEKEN / proveedor | Pendiente |
| Producción | Destino de copias de seguridad fuera del servidor | Backups | DEKEN | Pendiente |
| V2 | Apps OAuth oficiales: Meta (Instagram/Facebook Graph API), LinkedIn Marketing API, YouTube Data API, TikTok Content Posting API | Publicación | DEKEN (cuentas de empresa verificadas) | Fuera de V1 |

## 3. Variables de entorno de referencia

La lista completa, con valores por defecto de desarrollo, está en
[`infra/.env.example`](../infra/.env.example).
