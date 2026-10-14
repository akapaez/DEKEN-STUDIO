# Modelo de datos

PostgreSQL 16 es la fuente de verdad. Migraciones Alembic en `infra/migrations/`
(versionadas, reversibles, comprobadas sin deriva en `test_migrations.py`).

Convenciones: claves primarias UUID v4 (salvo tablas de eventos, `BIGINT IDENTITY`),
fechas `timestamptz` en UTC, enumeraciones como `VARCHAR` + `CHECK` (migraciones simples),
JSON en `JSONB`, nombres de restricciones deterministas (`pk_`, `fk_`, `uq_`, `ck_`, `ix_`).

## 1. Implementado en Sprint 0 (migración `0001`)

```mermaid
erDiagram
    users ||--o{ user_sessions : "tiene"
    users ||--o{ workers : "registra"
    users ||--o{ jobs : "crea"
    workers ||--o{ jobs : "lease"
    jobs ||--o{ job_events : "historial"
    jobs ||--o{ job_outputs : "salidas"
    job_outputs }o--|| stored_objects : "apunta a"
    jobs ||--o{ stored_objects : "genera"
```

### `users`
| Columna | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| email | varchar(320) único | siempre en minúsculas (`CHECK`) |
| full_name | varchar(200) | |
| password_hash | varchar(255) | argon2id |
| role | varchar(16) | `admin` · `editor` · `reviewer` · `viewer` |
| is_active | bool | desactivar revoca sus sesiones al instante |
| created_at / updated_at / last_login_at / password_changed_at | timestamptz | |

### `user_sessions`
Sesiones de servidor. La cookie lleva un token aleatorio de 256 bits; aquí solo se guarda
su SHA-256 (`token_hash`, único). Caducidad absoluta (`expires_at`, 7 días por defecto) y
por inactividad (`last_seen_at`, 12 h). `revoked_at` + `revoked_reason` (`logout`,
`password_changed`, `user_deactivated`, `password_reset_by_admin`).

### `audit_events` (solo inserción)
`id`, `occurred_at`, `actor_type` (`user|worker|system|anonymous`), `actor_id`,
`actor_label`, `action` (p. ej. `auth.login`, `user.role_change`, `worker.register`,
`job.cancel`, `file.download_url`, `authz.denied`), `outcome`
(`success|failure|denied`), `target_type`, `target_id`, `ip`, `user_agent`,
`request_id`, `details` JSONB. Un *trigger* impide `UPDATE` y `DELETE`.

### `workers`
`name` único, `token_prefix` (para identificarlo en la interfaz), `token_hash` (SHA-256),
`status` (`active|revoked`), `queues` (array), `capabilities` JSONB (versiones de
FFmpeg, codificadores, aceleración por hardware, tipos de trabajo), `version`,
`hostname`, `platform`, `last_seen_at`, `created_by_user_id`, `revoked_at`.

### `jobs`
| Columna | Notas |
|---|---|
| type, queue | p. ej. `system.render_selftest` en `render` |
| status | `queued` · `processing` · `completed` · `failed` · `cancelled` |
| priority | mayor primero |
| payload | validado por el modelo Pydantic del tipo (contrato compartido) |
| result / error | JSONB; `error` = `{code, message, retryable, details, attempt}` |
| progress, progress_message | 0..1 (`CHECK`) |
| attempts, max_attempts | reintentos con backoff exponencial |
| run_after | no se reclama antes (backoff) |
| lease_owner_id, lease_expires_at | propiedad temporal del worker |
| cancel_requested | cancelación cooperativa |
| timeout_s, contract_version | |
| created_by_user_id, created_at, updated_at, started_at, finished_at | |

Índices parciales: `ix_jobs_claimable (queue, priority, created_at) WHERE status='queued'`
y `ix_jobs_lease (lease_expires_at) WHERE status='processing'`.

### `job_events`
Historial por trabajo: `created`, `claimed`, `progress` (solo cambios de mensaje),
`output_registered`, `retry_scheduled`, `lease_expired`, `cancel_requested`,
`cancelled`, `verification_failed`, `failed`, `completed`, `manual_retry`.

### `stored_objects`
Objeto en S3: `bucket` + `key` (únicos, **generados por el servidor**), `kind`
(`original|derived|render|brand|system_test`), `status`
(`pending|available|rejected|deleted`), `content_type`, `size_bytes`, `sha256`,
`original_filename` (saneado, solo metadato), `media_info` (resumen ffprobe),
`verified_at`, `created_by_user_id`, `created_by_job_id`. Solo los `available` se pueden
descargar.

### `job_outputs`
Una fila por salida declarada y por intento (`job_id`, `attempt`, `name` únicos),
con `object_id`, `kind`, `verified` y `verification` (problemas detectados).

## 2. Evolución prevista (se añadirá con migraciones nuevas)

| Sprint | Tablas | Campos clave |
|---|---|---|
| 1 | `media_assets` | `original_object_id`, `title`, `recorded_at`, `location`, `consent_status` (personas grabadas), `source` (siempre material propio), `tags`, `duration_s`, `width`, `height`, `fps`, `has_audio`, `status` (`uploading`→`probing`→`ready`/`rejected`) |
| 1 | `media_derivatives` | `asset_id`, `kind` (`poster`, `strip`, `proxy_540p`, `waveform`), `object_id` |
| 1 | `brand_assets` | `kind` (`logo`, `font`, `music`), `variant`, `measured_color`, `aspect_ratio`, `license_ref` (obligatorio para música), `object_id` |
| 2 | `knowledge_sources` | `title`, `kind` (`document`, `url`, `note`), `object_id`/`url`, `owner_user_id`, `verified_at`, `verified_by` |
| 2 | `knowledge_facts` | `source_id`, `statement`, `status` (`proposed`/`approved`/`retired`), `approved_by` |
| 2 | `campaigns` | `name`, `objective`, `audience`, `starts_on`, `ends_on`, `status` |
| 2 | `content_items` | `campaign_id`, `objective`, `audience`, `platform`, `format`, `duration_s`, `key_message`, `cta`, `approval_status` (`draft`→`in_review`→`approved`/`changes_requested`), `scheduled_for` |
| 2 | `scripts`, `storyboard_shots` | guion versionado; planos temporizados con `fact_ids` citados |
| 2 | `approvals` | `content_id`, `decision`, `reviewer_id`, `comment` |
| 3 | `media_segments` | `asset_id`, `start_s`, `end_s`, `kind` (`scene`, `speech`, `silence`, `black`, `blur`), `score`, `labels`, `transcript` |
| 3 | `projects` | `title`, `content_id`, `aspect`, `target_duration_s` |
| 3 | `timeline_versions` | `project_id`, `version`, `document` (JSON timeline v1), `created_by`; inmutables |
| 3 | `renders` | `timeline_version_id`, `job_id`, `output_object_id` |
| V2 | `social_accounts`, `publications`, `metrics`, `leads` | OAuth oficial; datos personales de leads con base legal y retención |
