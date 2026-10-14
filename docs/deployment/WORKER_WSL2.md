# Worker local en Windows con WSL2

El worker es un proceso que **solo abre conexiones salientes** hacia la API (HTTPS) y
hacia el almacenamiento (URLs firmadas). No necesita puertos abiertos, VPN ni
credenciales de base de datos o de almacenamiento.

## 1. Preparar WSL2 (una vez)

En PowerShell como administrador:

```powershell
wsl --install -d Ubuntu-24.04
```

Dentro de Ubuntu:

```bash
sudo apt update && sudo apt install -y ffmpeg git curl
curl -LsSf https://astral.sh/uv/install.sh | sh     # instala uv
git clone <repositorio> deken-studio && cd deken-studio
uv sync --package deken-render
ffmpeg -hide_banner -encoders | grep -E "libx264|aac"   # deben aparecer
```

GPU NVIDIA (opcional): con el controlador de Windows actualizado, WSL2 expone la GPU; si
el FFmpeg instalado incluye `h264_nvenc`, el worker lo declara en sus capacidades. No es
necesario para V1.

## 2. Registrar el worker

1. En la web: *Configuración → Workers → Registrar un worker* (nombre del equipo, colas).
2. Copia el token `dkw_…` (se muestra **una sola vez**).

## 3. Configurar y comprobar

```bash
cat > ~/.deken-worker.env <<EOF2
DEKEN_API_URL=https://studio.ejemplo-deken.es
DEKEN_WORKER_TOKEN=dkw_...
DEKEN_WORKER_QUEUES=render,analysis
DEKEN_WORK_DIR=/home/$USER/deken-work
EOF2
chmod 600 ~/.deken-worker.env
set -a; . ~/.deken-worker.env; set +a
uv run deken-worker check     # capacidades + conexión con la API
uv run deken-worker run       # bucle de trabajo (Ctrl+C termina tras el trabajo actual)
```

Si la red corporativa usa un proxy con CA propia: `DEKEN_CA_BUNDLE=/ruta/ca.pem`.

## 4. Arranque automático (systemd en WSL2)

Activa systemd en `/etc/wsl.conf` (`[boot]\nsystemd=true`), reinicia WSL y crea
`~/.config/systemd/user/deken-worker.service`:

```ini
[Unit]
Description=DEKEN STUDIO AI worker
After=network-online.target

[Service]
EnvironmentFile=%h/.deken-worker.env
WorkingDirectory=%h/deken-studio
ExecStart=%h/.local/bin/uv run deken-worker run
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

```bash
systemctl --user enable --now deken-worker
loginctl enable-linger $USER
journalctl --user -u deken-worker -f
```

## 5. Comportamiento ante fallos

- Sin red: reintenta con espera exponencial (hasta 60 s) sin perder el trabajo en curso.
- PC apagado a mitad de un trabajo: la API detecta el lease vencido (~2 min) y lo vuelve a
  poner en cola (o lo marca fallido si agotó los intentos).
- Token revocado: el worker se detiene con un error claro.
- Directorios temporales: uno por trabajo (permisos 700), borrado siempre al terminar.
