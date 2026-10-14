# ADR 0002 — Sesiones de servidor con cookie opaca

- Estado: aceptada (Sprint 0)

## Contexto
Aplicación privada, pocos usuarios, misma web y API bajo el mismo origen. Se necesita
revocar el acceso de inmediato (bajas, cambios de rol, contraseñas comprometidas).

## Decisión
Token aleatorio de 256 bits en cookie HttpOnly; en BD solo su SHA-256. Cada petición
valida la sesión (una consulta indexada). CSRF por token HMAC de la sesión + `Origin`.

## Alternativas descartadas
JWT de acceso + refresh: complejidad (rotación, listas de revocación) sin beneficio para
este volumen; la revocación no sería inmediata.

## Consecuencias
Revocación instantánea y auditable; una consulta por petición (despreciable).
