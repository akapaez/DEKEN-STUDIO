"""Utilidades de prueba compartidas (tests de integración y E2E).

Solo se usan desde `tests/`; no forman parte del camino de producción.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass
from typing import Any, TypeVar

import httpx

from deken_api.cli import alembic_config
from deken_api.security.rbac import Role
from deken_api.security.tokens import CSRF_HEADER
from deken_shared.jobs import CONTRACT_HEADER, JOB_CONTRACT_VERSION

TEST_PASSWORD = "Prueba-Integracion-2026"  # noqa: S105 - credencial de pruebas
ORIGIN = "http://localhost:3000"


@dataclass
class TestUser:
    __test__ = False  # no es una clase de tests de pytest

    id: uuid.UUID
    email: str
    role: Role
    password: str = TEST_PASSWORD


class ApiClient(httpx.AsyncClient):
    """Cliente con cookies de sesión y cabecera CSRF tras el login."""

    async def login(self, email: str, password: str = TEST_PASSWORD) -> httpx.Response:
        response = await self.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
            headers={"Origin": ORIGIN},
        )
        if response.status_code == 200:
            self.headers[CSRF_HEADER] = response.json()["csrf_token"]
        return response


@dataclass
class TestWorker:
    __test__ = False

    id: uuid.UUID
    token: str

    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            CONTRACT_HEADER: str(JOB_CONTRACT_VERSION),
        }


@dataclass
class LiveServer:
    url: str


ClientFactory = Callable[[], Awaitable[ApiClient]]
UserFactory = Callable[..., Awaitable[TestUser]]
WorkerFactory = Callable[..., Awaitable[TestWorker]]


T = TypeVar("T")


def run_sync[T](coro: Coroutine[Any, Any, T]) -> T:
    """Ejecuta una corrutina en un hilo con su propio bucle (válido aunque ya haya uno)."""
    import asyncio

    result: list[T] = []
    errors: list[BaseException] = []

    def _target() -> None:
        try:
            result.append(asyncio.run(coro))
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=_target)
    thread.start()
    thread.join()
    if errors:
        raise errors[0]
    return result[0]


def run_alembic(database_url: str, action: str, revision: str | None = None) -> None:
    """Ejecuta un comando de Alembic en un hilo propio (env.py usa asyncio.run)."""
    from alembic import command
    from alembic.config import Config

    errors: list[BaseException] = []

    def _target() -> None:
        try:
            cfg = alembic_config()
            if not isinstance(cfg, Config):  # pragma: no cover
                raise TypeError("configuración de Alembic inesperada")
            cfg.attributes["database_url"] = database_url
            func = getattr(command, action)
            if revision is None:
                func(cfg)
            else:
                func(cfg, revision)
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=_target)
    thread.start()
    thread.join()
    if errors:
        raise errors[0]
