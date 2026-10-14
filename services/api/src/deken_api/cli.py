"""CLI de operación: `deken-api <comando>`.

Comandos:
  migrate          Aplica las migraciones pendientes (alembic upgrade head).
  init-storage     Crea el bucket si no existe.
  create-admin     Crea el primer administrador (pide la contraseña por teclado o la
                   lee de DEKEN_BOOTSTRAP_ADMIN_PASSWORD para automatización).
  check            Comprueba BD, Redis y almacenamiento (código de salida ≠ 0 si falla).
  export-openapi   Escribe el esquema OpenAPI en un fichero.
  storage-backup   Copia incremental del bucket a un directorio local.
  storage-restore  Sube a un bucket los objetos de una copia que falten.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import os
import sys
from pathlib import Path

from deken_api.config import get_settings
from deken_api.context import AppContext
from deken_api.errors import ApiError
from deken_api.security.rbac import Role
from deken_api.services import system as system_service
from deken_api.services import users as users_service
from deken_api.services.audit import Actor, AuditContext

API_DIR = Path(__file__).resolve().parents[2]


def alembic_config() -> object:
    from alembic.config import Config

    ini = os.environ.get("DEKEN_ALEMBIC_INI") or str(API_DIR / "alembic.ini")
    return Config(ini)


def cmd_migrate(_: argparse.Namespace) -> int:
    from alembic import command

    command.upgrade(alembic_config(), "head")  # type: ignore[arg-type]
    return 0


async def _init_storage() -> int:
    ctx = AppContext.create(get_settings())
    try:
        created = await ctx.storage.ensure_bucket()
        print(f"Bucket '{ctx.storage.bucket}' {'creado' if created else 'ya existía'}")
        return 0
    finally:
        await ctx.close()


def cmd_init_storage(_: argparse.Namespace) -> int:
    return asyncio.run(_init_storage())


async def _create_admin(email: str, name: str, password: str) -> int:
    ctx = AppContext.create(get_settings())
    try:
        async with ctx.sessionmaker() as db:
            user = await users_service.create_user(
                db,
                AuditContext(Actor.system()),
                email=email,
                full_name=name,
                role=Role.ADMIN,
                password=password,
            )
        print(f"Administrador creado: {user.email} ({user.id})")
        return 0
    except ApiError as exc:
        print(f"Error: {exc.message}", file=sys.stderr)
        return 1
    finally:
        await ctx.close()


def cmd_create_admin(args: argparse.Namespace) -> int:
    password = os.environ.get("DEKEN_BOOTSTRAP_ADMIN_PASSWORD")
    if not password:
        password = getpass.getpass("Contraseña (mín. 12 caracteres): ")
        if password != getpass.getpass("Repite la contraseña: "):
            print("Las contraseñas no coinciden", file=sys.stderr)
            return 1
    return asyncio.run(_create_admin(args.email, args.name, password))


async def _check() -> int:
    ctx = AppContext.create(get_settings())
    try:
        checks = await system_service.readiness(ctx)
    finally:
        await ctx.close()
    overall = system_service.overall_status(checks)
    print(json.dumps({"status": overall, "checks": checks}, indent=2, default=str))
    return 0 if overall != "error" else 1


def cmd_check(_: argparse.Namespace) -> int:
    return asyncio.run(_check())


def cmd_export_openapi(args: argparse.Namespace) -> int:
    from deken_api.config import Settings
    from deken_api.main import create_app

    # El esquema no depende de la configuración: se usan valores neutros y no se
    # conecta a ningún servicio (la app no se arranca).
    neutral = Settings(secret_key="openapi-export-" + "0" * 32, log_json=False)  # type: ignore[arg-type]
    schema = create_app(neutral, run_reaper=False).openapi()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"OpenAPI escrita en {out}")
    return 0


def _safe_target(root: Path, key: str) -> Path:
    target = (root / key).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"clave de objeto no segura: {key}")
    return target


def cmd_storage_backup(args: argparse.Namespace) -> int:
    """Réplica incremental: descarga solo los objetos nuevos o con tamaño distinto."""
    settings = get_settings()
    ctx = AppContext.create(settings)
    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)
    s3 = ctx.storage.internal
    copied = skipped = 0
    try:
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=ctx.storage.bucket):
            for obj in page.get("Contents", []):
                key, size = obj["Key"], int(obj["Size"])
                target = _safe_target(dest, key)
                if target.exists() and target.stat().st_size == size:
                    skipped += 1
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                s3.download_file(ctx.storage.bucket, key, str(target))
                copied += 1
    finally:
        asyncio.run(ctx.close())
    print(json.dumps({"bucket": ctx.storage.bucket, "copied": copied, "unchanged": skipped}))
    return 0


def cmd_storage_restore(args: argparse.Namespace) -> int:
    settings = get_settings()
    ctx = AppContext.create(settings)
    src = Path(args.src)
    s3 = ctx.storage.internal
    uploaded = present = 0
    try:
        asyncio.run(ctx.storage.ensure_bucket())
        for path in sorted(p for p in src.rglob("*") if p.is_file()):
            key = path.relative_to(src).as_posix()
            if asyncio.run(ctx.storage.head(key)) is not None:
                present += 1
                continue
            s3.upload_file(str(path), ctx.storage.bucket, key)
            uploaded += 1
    finally:
        asyncio.run(ctx.close())
    print(
        json.dumps({"bucket": ctx.storage.bucket, "uploaded": uploaded, "already_present": present})
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="deken-api")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate").set_defaults(func=cmd_migrate)
    sub.add_parser("init-storage").set_defaults(func=cmd_init_storage)
    admin = sub.add_parser("create-admin")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", required=True)
    admin.set_defaults(func=cmd_create_admin)
    sub.add_parser("check").set_defaults(func=cmd_check)
    export = sub.add_parser("export-openapi")
    export.add_argument("--out", required=True)
    export.set_defaults(func=cmd_export_openapi)
    backup = sub.add_parser("storage-backup")
    backup.add_argument("--dest", required=True)
    backup.set_defaults(func=cmd_storage_backup)
    restore = sub.add_parser("storage-restore")
    restore.add_argument("--src", required=True)
    restore.set_defaults(func=cmd_storage_restore)
    args = parser.parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())
