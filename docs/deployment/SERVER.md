# Despliegue en servidor (V1)

Topología: un servidor Linux con Docker Compose (`infra/docker-compose.yml`, perfil
`app`) detrás de un proxy TLS. El worker puede ir en el mismo servidor (perfil `worker`)
o en el PC de DEKEN con WSL2.

```
Internet ──TLS──> Caddy ──/api/*──> api:8000
                        └──/*──────> web:3000
                  storage.dominio ──> seaweedfs:8333 (URLs firmadas)
```

Ejemplo de `Caddyfile`:

```
studio.ejemplo-deken.es {
  encode zstd gzip
  handle /api/* { reverse_proxy api:8000 }
  handle { reverse_proxy web:3000 }
}
files.ejemplo-deken.es {
  reverse_proxy seaweedfs:8333
}
```

Variables mínimas de producción (además de las de `infra/.env.example`):

```
DEKEN_ENVIRONMENT=production
DEKEN_ALLOWED_ORIGINS=https://studio.ejemplo-deken.es
S3_PUBLIC_ENDPOINT_URL=https://files.ejemplo-deken.es
S3_WORKER_ENDPOINT_URL=https://files.ejemplo-deken.es
S3_ALLOWED_ORIGINS=https://studio.ejemplo-deken.es
DEKEN_FORWARDED_ALLOW_IPS=<IP del proxy>
```

Y en la web: `DEKEN_MEDIA_ORIGINS=https://files.ejemplo-deken.es` (CSP de vídeo/imagen).

Recursos orientativos: 4 vCPU, 8 GB RAM, disco para vídeo (originales + derivados ≈ 2×
el volumen grabado). Copias: ver `docs/operations/BACKUP_RESTORE.md`.
