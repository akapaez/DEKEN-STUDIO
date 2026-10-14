"""Fixtures de integración: PostgreSQL, Redis y S3 reales.

Variables:
  DEKEN_TEST_DATABASE_URL  URL asyncpg a un servidor PostgreSQL (se crea una BD temporal).
  DEKEN_TEST_REDIS_URL     URL de Redis/Valkey (se usa la BD 15 y se vacía entre tests).
  DEKEN_TEST_S3_ENDPOINT_URL / _ACCESS_KEY / _SECRET_KEY
                           S3 compatible. Si no se define, se arranca moto en proceso.

Sin DEKEN_TEST_DATABASE_URL los tests de integración se omiten (no se simulan).
"""

from __future__ import annotations

import asyncio
import os
import socket
import threading
import time
import uuid
from collections.abc import AsyncIterator, Iterator

import asyncpg
import httpx
import pytest
import uvicorn
from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy import text

from deken_api.config import Environment, Settings
from deken_api.context import AppContext
from deken_api.main import create_app
from deken_api.security.rbac import Role
from deken_api.services import users as users_service
from deken_api.services import workers as workers_service
from deken_api.services.audit import Actor, AuditContext
from deken_api.testing import (
    ORIGIN,
    TEST_PASSWORD,
    ApiClient,
    ClientFactory,
    LiveServer,
    TestUser,
    TestWorker,
    UserFactory,
    WorkerFactory,
    run_alembic,
    run_sync,
)
from deken_shared.jobs import Queue

TABLES = [
    "job_outputs",
    "stored_objects",
    "job_events",
    "jobs",
    "workers",
    "user_sessions",
    "users",
    "audit_events",
]


# --- Infraestructura ----------------------------------------------------------------------


def _plain(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    base = os.environ["DEKEN_TEST_DATABASE_URL"]
    name = f"deken_test_{uuid.uuid4().hex[:10]}"

    async def _admin(sql: str) -> None:
        conn = await asyncpg.connect(_plain(base))
        try:
            await conn.execute(sql)
        finally:
            await conn.close()

    run_sync(_admin(f'CREATE DATABASE "{name}"'))
    prefix, _, _ = base.rpartition("/")
    url = f"{prefix}/{name}"
    yield url
    run_sync(_admin(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))


@pytest.fixture(scope="session")
def migrated_database(database_url: str) -> str:
    run_alembic(database_url, "upgrade", "head")
    return database_url


@pytest.fixture(scope="session")
def s3_config() -> Iterator[dict[str, str]]:
    endpoint = os.environ.get("DEKEN_TEST_S3_ENDPOINT_URL")
    if endpoint:
        yield {
            "endpoint": endpoint,
            "access_key": os.environ["DEKEN_TEST_S3_ACCESS_KEY"],
            "secret_key": os.environ["DEKEN_TEST_S3_SECRET_KEY"],
        }
        return
    from moto.server import ThreadedMotoServer

    port = _free_port()
    server = ThreadedMotoServer(ip_address="127.0.0.1", port=port)
    server.start()
    try:
        yield {
            "endpoint": f"http://127.0.0.1:{port}",
            "access_key": "test-access",
            "secret_key": "test-secret",
        }
    finally:
        server.stop()


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def settings(migrated_database: str, s3_config: dict[str, str]) -> Settings:
    return Settings(
        environment=Environment.TEST,
        log_json=False,
        log_level="WARNING",
        secret_key="test-secret-key-0123456789-abcdefghijklmnopqrstuvwxyz",  # type: ignore[arg-type]
        database_url=migrated_database,
        database_pool_size=5,
        redis_url=os.environ.get("DEKEN_TEST_REDIS_URL", "redis://localhost:6379/15"),
        s3_endpoint_url=s3_config["endpoint"],
        s3_access_key=s3_config["access_key"],  # type: ignore[arg-type]
        s3_secret_key=s3_config["secret_key"],  # type: ignore[arg-type]
        s3_public_endpoint_url=None,
        s3_worker_endpoint_url=None,
        s3_bucket=f"deken-test-{uuid.uuid4().hex[:8]}",
        ai_provider=None,
        ai_api_key=None,
        allowed_origins=[ORIGIN],
        job_retry_base_seconds=0,
        job_lease_seconds=30,
    )


@pytest.fixture(scope="session")
async def app(settings: Settings) -> AsyncIterator[FastAPI]:
    application = create_app(settings, run_reaper=False)
    async with application.router.lifespan_context(application):
        ctx: AppContext = application.state.ctx
        await ctx.storage.ensure_bucket()
        try:
            yield application
        finally:
            await asyncio.to_thread(_delete_bucket, ctx)


def _delete_bucket(ctx: AppContext) -> None:
    """Borra el bucket temporal de la sesión de tests (y libera sus volúmenes)."""
    s3 = ctx.storage.internal
    bucket = ctx.storage.bucket
    if not bucket.startswith("deken-test-"):
        return
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            s3.delete_object(Bucket=bucket, Key=obj["Key"])
    s3.delete_bucket(Bucket=bucket)


@pytest.fixture(scope="session")
def ctx(app: FastAPI) -> AppContext:
    context: AppContext = app.state.ctx
    return context


@pytest.fixture(autouse=True)
async def _clean_state(ctx: AppContext) -> None:
    """Cada test empieza con la base de datos y Redis vacíos."""
    context = ctx
    async with context.engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))
    redis: Redis = context.redis
    await redis.flushdb()


# --- Clientes y usuarios ------------------------------------------------------------------


@pytest.fixture
async def client_factory(app: FastAPI) -> AsyncIterator[ClientFactory]:
    clients: list[ApiClient] = []

    async def _make() -> ApiClient:
        client = ApiClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")
        clients.append(client)
        return client

    yield _make
    for client in clients:
        await client.aclose()


@pytest.fixture
async def client(client_factory: ClientFactory) -> ApiClient:
    return await client_factory()


@pytest.fixture
def make_user(ctx: AppContext) -> UserFactory:
    async def _make(role: Role = Role.ADMIN, email: str | None = None) -> TestUser:
        email = email or f"{role.value}-{uuid.uuid4().hex[:6]}@deken.test"
        async with ctx.sessionmaker() as db:
            user = await users_service.create_user(
                db,
                AuditContext(Actor.system()),
                email=email,
                full_name=f"Usuario {role.value}",
                role=role,
                password=TEST_PASSWORD,
            )
        return TestUser(id=user.id, email=user.email, role=role)

    return _make


@pytest.fixture
async def admin_client(client_factory: ClientFactory, make_user: UserFactory) -> ApiClient:
    user = await make_user(Role.ADMIN)
    client = await client_factory()
    response = await client.login(user.email)
    assert response.status_code == 200, response.text
    return client


@pytest.fixture
def make_worker(ctx: AppContext) -> WorkerFactory:
    async def _make(queues: list[Queue] | None = None, name: str | None = None) -> TestWorker:
        async with ctx.sessionmaker() as db:
            registered = await workers_service.register_worker(
                db,
                AuditContext(Actor.system()),
                name=name or f"worker-{uuid.uuid4().hex[:6]}",
                queues=queues or [Queue.RENDER, Queue.ANALYSIS],
            )
        return TestWorker(id=registered.worker.id, token=registered.token)

    return _make


# --- Servidor HTTP real (para el worker) ---------------------------------------------------


@pytest.fixture(scope="session")
def live_server(settings: Settings, app: FastAPI) -> Iterator[LiveServer]:
    """API real en un puerto local, con su propio bucle de eventos y recursos."""
    port = _free_port()
    config = uvicorn.Config(
        create_app(settings, run_reaper=False),
        host="127.0.0.1",
        port=port,
        log_level="warning",
        lifespan="on",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 20
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("el servidor de pruebas no arrancó")
        time.sleep(0.05)
    yield LiveServer(url=f"http://127.0.0.1:{port}")
    server.should_exit = True
    thread.join(timeout=10)
