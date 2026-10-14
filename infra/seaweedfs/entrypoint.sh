#!/bin/sh
# Genera la configuración de identidades S3 desde variables de entorno (sin secretos en
# el repositorio) y arranca SeaweedFS con master, volume, filer y pasarela S3.
set -eu
umask 077
mkdir -p /data /run/seaweedfs
cat > /run/seaweedfs/s3.json <<JSON
{
  "identities": [
    {
      "name": "deken-api",
      "credentials": [{"accessKey": "${S3_ACCESS_KEY}", "secretKey": "${S3_SECRET_KEY}"}],
      "actions": ["Admin", "Read", "Write", "List", "Tagging"]
    }
  ]
}
JSON
exec weed server \
  -dir=/data \
  -ip.bind=0.0.0.0 \
  -master.volumeSizeLimitMB="${SEAWEEDFS_VOLUME_SIZE_MB:-1024}" \
  -volume.max="${SEAWEEDFS_VOLUME_MAX:-200}" \
  -s3 \
  -s3.port=8333 \
  -s3.config=/run/seaweedfs/s3.json \
  -s3.allowedOrigins="${S3_ALLOWED_ORIGINS}"
