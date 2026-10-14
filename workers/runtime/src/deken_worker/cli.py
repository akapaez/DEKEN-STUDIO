"""CLI del worker.

deken-worker run [--once]   Procesa trabajos (bucle infinito por defecto).
deken-worker check          Muestra capacidades y comprueba la conexión con la API.
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
from types import FrameType

from deken_worker.capabilities import detect
from deken_worker.client import ApiClientError, WorkerClient
from deken_worker.config import WorkerSettings
from deken_worker.runtime import Worker, load_handlers


def _build() -> tuple[WorkerSettings, WorkerClient]:
    settings = WorkerSettings()  # valores desde el entorno
    client = WorkerClient(
        settings.api_url,
        settings.worker_token.get_secret_value(),
        timeout=settings.http_timeout_seconds,
        verify=settings.ca_bundle or True,
    )
    return settings, client


def cmd_check(_: argparse.Namespace) -> int:
    settings, client = _build()
    handlers = load_handlers()
    caps = detect(settings.ffmpeg_path, settings.ffprobe_path, list(handlers))
    print(json.dumps(caps.model_dump(), indent=2))
    worker = Worker(settings, client, handlers)
    try:
        worker.heartbeat()
    except ApiClientError as exc:
        print(f"La API rechazó el heartbeat: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()
    print("Conexión con la API correcta.")
    return 0 if caps.ffmpeg_version and caps.ffprobe_version else 1


def cmd_run(args: argparse.Namespace) -> int:
    settings, client = _build()
    worker = Worker(settings, client, load_handlers())

    def _stop(signum: int, _frame: FrameType | None) -> None:
        logging.getLogger("deken_worker").info(
            "Señal %d: terminando tras el trabajo actual", signum
        )
        worker.stop_event.set()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    try:
        if args.once:
            worker.heartbeat()
            worker.run_once()
        else:
            worker.run_forever()
    finally:
        client.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    # httpx registra las URLs completas en INFO; las firmadas no deben acabar en los logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(prog="deken-worker")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--once", action="store_true", help="Procesa como mucho un trabajo")
    run.set_defaults(func=cmd_run)
    sub.add_parser("check").set_defaults(func=cmd_check)
    args = parser.parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())
