# Seguridad

Guía de referencia: OWASP ASVS nivel 2 (revisión completa en Sprint 5).

## 1. Superficie y amenazas principales

| Activo | Amenaza | Control |
|---|---|---|
| Cuentas | Fuerza bruta, relleno de credenciales | argon2id, límite por email (10/15 min) y por IP (50/15 min) con Redis y respaldo en memoria, mensaje de error genérico, tiempo constante (hash ficticio si el usuario no existe) |
| Sesiones | Robo/reutilización de cookie | Token aleatorio de 256 bits, solo su hash en BD, HttpOnly, SameSite=Lax, Secure en producción, caducidad absoluta e inactividad, revocación inmediata (logout, desactivación, cambio de contraseña) |
| Peticiones con cookie | CSRF | Token por sesión (HMAC) en cabecera + comprobación de `Origin`; JSON obligatorio |
| Datos | Escalada de privilegios | RBAC en cada ruta de la API (la interfaz solo oculta); matriz probada por rol; denegaciones auditadas |
| Ficheros | Acceso no autorizado, rutas arbitrarias | Bucket privado; URLs firmadas de 5 min (descarga) / 15 min (subida); claves generadas por el servidor; nombres de descarga saneados |
| Subidas (Sprint 1) | Ficheros falsos, corruptos o maliciosos; agotamiento de almacenamiento | Extensión permitida (MP4/MOV; PNG/WebP/TTF/OTF en marca), tamaño máximo (20 GiB vídeo, 50 MiB marca), `ListParts` en servidor (no se confía en los ETag del navegador), ffprobe en la API sobre el objeto real, decodificación de muestra en la ingesta, Pillow con límite de 60 Mpx (bombas de descompresión), fontTools; los ficheros rechazados se borran; CORS del almacenamiento limitado a los orígenes de la web |
| Composiciones (Remotion) | Fuga de credenciales o lectura de ficheros ajenos desde el navegador del render | La composición solo recibe URLs de un servidor local (127.0.0.1, token aleatorio por render, confinado al directorio del trabajo, sin symlinks fuera); la especificación de render contiene rutas locales, nunca claves S3 ni URLs firmadas; la clave de licencia, si existe, solo en el worker y en un fichero 600 que se borra al terminar |
| Licencias | Uso comercial de Remotion sin licencia | Modo `evaluation` por defecto con triple comprobación (API, worker, renderer); renders de evaluación con marca de agua y en `evaluation/` (ADR 0005) |
| Workers | Token robado, worker malicioso | Token revocable de 256 bits (hash en BD), solo protocolo de workers, colas permitidas por worker, sin credenciales de BD/S3, verificación de salidas en servidor (no se confía en el worker) |
| Procesado de vídeo | Inyección de comandos, lectura de ficheros vía protocolos de FFmpeg | Listas de argumentos (sin shell), `-protocol_whitelist file` para entradas locales y `http,https,tcp,tls,crypto` solo para URLs firmadas propias, rutas confinadas al directorio del trabajo (incluye symlinks), timeouts y cancelación |
| API | Abuso de recursos | Límite de cuerpo (1 MiB), long-poll acotado (≤ 30 s), resultados de trabajos ≤ 64 KiB |
| Navegador | XSS, clickjacking | CSP estricta con nonce por petición y `strict-dynamic`, `frame-ancestors 'none'`, `nosniff`, sin `dangerouslySetInnerHTML` salvo el script de tema (con nonce) |
| Secretos | Fuga | Solo en entorno/ficheros (`*_FILE`), nunca en repositorio ni bundle (comprobación automática `check-secrets`); logs sin URLs firmadas |
| Auditoría | Manipulación | Tabla de solo inserción protegida por *trigger* |
| Datos | Pérdida | Copias diarias de BD + réplica de objetos; restauración probada |

## 2. Roles y permisos (Sprints 0–1)

| Permiso | admin | editor | reviewer | viewer |
|---|:-:|:-:|:-:|:-:|
| `system:read` (estado, workers, motor de render) | ✅ | ✅ | ✅ | ✅ |
| `jobs:read` | ✅ | ✅ | ✅ | ✅ |
| `files:read` | ✅ | ✅ | ✅ | ✅ |
| `media:read` (biblioteca, proxy, original) | ✅ | ✅ | ✅ | ✅ |
| `brand:read` | ✅ | ✅ | ✅ | ✅ |
| `jobs:manage` (cancelar/reintentar) | ✅ | ✅ | | |
| `media:write` (subir, catalogar, archivar) | ✅ | ✅ | | |
| `render:create` (renders de línea de tiempo) | ✅ | ✅ | | |
| `media:rights` (derechos de imagen y consentimiento) | ✅ | | ✅ | |
| `brand:manage` (recursos oficiales de marca) | ✅ | | | |
| `system:manage` (autotest, evaluación de Remotion) | ✅ | | | |
| `users:manage` | ✅ | | | |
| `workers:manage` | ✅ | | | |
| `audit:read` | ✅ | | | |

La matriz se prueba ruta a ruta en `test_rbac_users_audit.py::test_permission_matrix`.
Los derechos de imagen los decide quien revisa (no quien sube): separación de funciones.
Previstos: `content:write` (admin, editor — S2), `content:approve` (admin, reviewer —
S2), `publish` (admin, reviewer — V2). Siempre debe quedar al menos un administrador activo.

## 3. Secretos

- Desarrollo: `make env` genera `infra/.env` con valores aleatorios (permisos 600).
- Producción: Docker secrets o gestor de secretos → variables `DEKEN_*_FILE`.
- Rotación del `DEKEN_SECRET_KEY`: invalida los tokens CSRF (los usuarios recargan); las
  sesiones siguen en BD.
- Claves de proveedores (IA, redes sociales) solo en la API; el navegador nunca las ve.

## 4. Datos personales (RGPD)

- V1 solo trata datos de usuarios internos (nombre, email, IP en auditoría).
- Grabaciones con personas (Sprint 1): por activo se registra si aparecen personas, el
  estado del consentimiento, su **referencia documental** (obligatoria para concederlo),
  restricciones y titular; cada cambio queda auditado con el antes/después. Salvo que
  conste que no aparecen personas, el activo solo se puede usar en renders de producción
  con el consentimiento concedido (o marcado como no requerido); si no, la API responde
  `unauthorized_media`. Un consentimiento denegado lo excluye siempre.
- Proveedor de IA: no se envían datos personales; solo hechos aprobados y textos de
  trabajo. Revisar el contrato de tratamiento del proveedor antes de activarlo.
- Leads (V2): base legal, finalidad y plazo de conservación definidos antes de implementar.

## 5. Despliegue seguro (lista de comprobación)

- [ ] `DEKEN_ENVIRONMENT=production` (exige cookies Secure y orígenes HTTPS).
- [ ] TLS en el proxy; HSTS activo; `/api/docs` deshabilitado (automático en producción).
- [ ] `DEKEN_FORWARDED_ALLOW_IPS` = IP del proxy (no `*`).
- [ ] Puertos de PostgreSQL, Redis y S3 no expuestos a Internet.
- [ ] Contraseña en Redis/Valkey; usuario S3 limitado al bucket.
- [ ] Copias fuera del servidor y prueba de restauración trimestral.
- [ ] Imágenes con versión fijada (digest) y actualizaciones de seguridad mensuales.

## 6. Notificación de incidentes

1. Revocar tokens/sesiones afectados (usuarios: desactivar; workers: revocar).
2. Rotar secretos comprometidos.
3. Exportar `audit_events` del periodo.
4. Si hay datos personales afectados, notificar a la AEPD en 72 h cuando proceda.
