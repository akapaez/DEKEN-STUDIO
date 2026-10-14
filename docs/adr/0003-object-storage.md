# ADR 0003 — Almacenamiento S3 genérico; SeaweedFS en desarrollo

- Estado: aceptada (Sprint 0)

## Decisión
- La API usa la interfaz S3 (boto3) y URLs firmadas; ningún componente depende de un
  proveedor concreto.
- Desarrollo y servidor propio: **SeaweedFS** (Apache-2.0).
- Producción gestionada (opcional): AWS S3, Cloudflare R2, Wasabi u otro compatible.
- Endpoints distintos para la API (interno), el navegador y los workers, porque las URLs
  firmadas incluyen el host.

## Alternativas descartadas
- **MinIO**: AGPL-3.0 y la edición comunitaria dejó de distribuir binarios e imágenes
  oficiales en 2025; mantenimiento incierto.
- **Sistema de ficheros local**: no permite URLs firmadas ni workers remotos.

## Consecuencias
Cada bucket de SeaweedFS es una colección con volúmenes propios: se fija
`SEAWEEDFS_VOLUME_MAX` alto (los volúmenes no reservan disco).
