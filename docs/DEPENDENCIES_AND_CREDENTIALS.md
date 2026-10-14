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

## 2. Dependencias externas por sprint

| Sprint | Dependencia | Necesaria para | Quién la aporta | Estado |
|---|---|---|---|---|
| 0 | Ninguna | — | — | ✅ |
| 1 | Grabaciones reales (`Deken-Recursos/Videos-bruto`) | Aceptación manual de importación | DEKEN | Pendiente de recibir en el servidor |
| 1 | Logos oficiales (`Deken-Recursos/Versiones-Logo`) y `.ttf` de Montserrat | Marca DEKEN | DEKEN | Pendiente |
| 1 | Consentimientos de imagen de personas que aparecen en grabaciones | Uso de esos planos | DEKEN (RR. HH./legal) | Pendiente |
| 2 | Clave API del proveedor IA (`DEKEN_AI_PROVIDER`, `DEKEN_AI_API_KEY`, `DEKEN_AI_MODEL`) | Director IA (opcional: sin ella, modo manual) | DEKEN contrata la cuenta | Pendiente |
| 2 | Fuentes verificadas: fichas técnicas Schüco de los sistemas que DEKEN fabrica, certificados reales, catálogo propio | Base de conocimiento | DEKEN (dirección técnica) | Pendiente |
| 3 | Modelo Whisper (descarga única, ~1,5 GB `large-v3` o ~150 MB `small`) | Transcripción local | Descarga automática en el worker | — |
| 3/4 | Biblioteca musical con licencia (o ninguna) | Música en renders | DEKEN | Pendiente; sin ella los renders van sin música |
| 3 | Licencia Remotion *Company License* | Solo si se activa el motor Remotion | DEKEN | **No contratada** → motor desactivado |
| Producción | Dominio + certificado TLS, servidor (≥ 4 vCPU, 8 GB, almacenamiento para vídeo) | Despliegue | DEKEN / proveedor | Pendiente |
| Producción | Destino de copias de seguridad fuera del servidor | Backups | DEKEN | Pendiente |
| V2 | Apps OAuth oficiales: Meta (Instagram/Facebook Graph API), LinkedIn Marketing API, YouTube Data API, TikTok Content Posting API | Publicación | DEKEN (cuentas de empresa verificadas) | Fuera de V1 |

## 3. Variables de entorno de referencia

La lista completa, con valores por defecto de desarrollo, está en
[`infra/.env.example`](../infra/.env.example).
