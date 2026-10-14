# ADR 0001 — Cola de trabajos en PostgreSQL con protocolo HTTP para workers

- Estado: aceptada (Sprint 0)

## Contexto
El procesamiento de vídeo se hará al principio en un PC con Windows/WSL2 de DEKEN, sin
puertos abiertos, y más adelante también en la nube. Hay que registrar estados,
progreso, errores, reintentos y salidas, y no dar un trabajo por completado sin verificar
el fichero.

## Decisión
- PostgreSQL es la fuente de verdad de los trabajos (`jobs`, `job_events`, `job_outputs`).
- Los workers no se conectan a PostgreSQL, Redis ni S3: usan un protocolo HTTPS de la API
  (claim con long-poll, progreso/lease, URLs firmadas para salidas, complete/fail).
- Reparto con `SELECT … FOR UPDATE SKIP LOCKED`; Redis solo despierta a los long-polls.
- La API verifica cada salida (existencia, tamaño, SHA-256 y ffprobe).

## Alternativas descartadas
- **Celery/RQ/Arq sobre Redis**: exigirían exponer Redis al worker remoto y dar
  credenciales de infraestructura a una máquina de oficina; el estado quedaría en un
  sistema no transaccional.
- **Colas gestionadas (SQS, Pub/Sub)**: atan a un proveedor y añaden credenciales.

## Consecuencias
- Un único contrato sirve para local y nube; sin puertos entrantes en el worker.
- Si Redis cae, los workers siguen funcionando por sondeo (latencia de hasta 5 s).
- El rendimiento de PostgreSQL como cola es más que suficiente para el volumen de DEKEN
  (decenas de trabajos al día).
