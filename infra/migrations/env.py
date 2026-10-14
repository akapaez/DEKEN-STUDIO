"""Entorno de Alembic (asíncrono). La URL sale de la configuración de la API."""

from __future__ import annotations

import asyncio
import os

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from deken_api.db import models  # noqa: F401  (registra las tablas en el metadata)
from deken_api.db.base import Base

config = context.config
target_metadata = Base.metadata


def database_url() -> str:
    url = config.attributes.get("database_url") or os.environ.get("DEKEN_DATABASE_URL")
    if url:
        return str(url)
    from deken_api.config import get_settings

    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(database_url())
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
