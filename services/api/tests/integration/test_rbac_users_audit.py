"""S0-05 (matriz de permisos), S0-08 (auditoría) y gestión de usuarios."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from deken_api.context import AppContext
from deken_api.db.models import AuditEvent
from deken_api.security.rbac import ROLE_PERMISSIONS, Permission, Role
from deken_api.testing import ApiClient, ClientFactory, UserFactory

pytestmark = pytest.mark.integration

_ID = uuid.uuid4()

# (método, ruta, cuerpo, permiso requerido)
PROTECTED: list[tuple[str, str, dict[str, object] | None, Permission]] = [
    ("GET", "/api/v1/system/status", None, Permission.SYSTEM_READ),
    ("POST", "/api/v1/system/selftest", {}, Permission.SYSTEM_MANAGE),
    ("GET", "/api/v1/users", None, Permission.USERS_MANAGE),
    (
        "POST",
        "/api/v1/users",
        {"email": "x@deken.test", "full_name": "X", "role": "viewer", "password": "x"},
        Permission.USERS_MANAGE,
    ),
    ("PATCH", f"/api/v1/users/{_ID}", {"full_name": "Y"}, Permission.USERS_MANAGE),
    ("POST", f"/api/v1/users/{_ID}/password", {"password": "x"}, Permission.USERS_MANAGE),
    ("GET", "/api/v1/workers", None, Permission.SYSTEM_READ),
    ("POST", "/api/v1/workers", {"name": "abc", "queues": ["render"]}, Permission.WORKERS_MANAGE),
    ("POST", f"/api/v1/workers/{_ID}/revoke", None, Permission.WORKERS_MANAGE),
    ("GET", "/api/v1/jobs", None, Permission.JOBS_READ),
    ("GET", f"/api/v1/jobs/{_ID}", None, Permission.JOBS_READ),
    ("POST", f"/api/v1/jobs/{_ID}/cancel", None, Permission.JOBS_MANAGE),
    ("POST", f"/api/v1/jobs/{_ID}/retry", None, Permission.JOBS_MANAGE),
    ("GET", f"/api/v1/files/{_ID}/download-url", None, Permission.FILES_READ),
    ("GET", "/api/v1/audit", None, Permission.AUDIT_READ),
]


@pytest.mark.parametrize("role", list(Role))
async def test_permission_matrix(
    role: Role, client_factory: ClientFactory, make_user: UserFactory
) -> None:
    user = await make_user(role)
    client = await client_factory()
    await client.login(user.email)
    for method, path, body, permission in PROTECTED:
        response = await client.request(method, path, json=body)
        allowed = permission in ROLE_PERMISSIONS[role]
        if allowed:
            assert response.status_code != 403, (role, method, path, response.text)
        else:
            assert response.status_code == 403, (role, method, path, response.status_code)
            assert response.json()["error"]["code"] == "permission_denied"


async def test_denied_access_is_audited(
    client_factory: ClientFactory, make_user: UserFactory, ctx: AppContext
) -> None:
    user = await make_user(Role.VIEWER)
    client = await client_factory()
    await client.login(user.email)
    assert (await client.get("/api/v1/audit")).status_code == 403
    async with ctx.sessionmaker() as db:
        event = (
            await db.execute(select(AuditEvent).where(AuditEvent.action == "authz.denied"))
        ).scalar_one()
    assert event.actor_id == user.id
    assert event.details["permission"] == "audit:read"


async def test_user_lifecycle_is_audited(admin_client: ApiClient, ctx: AppContext) -> None:
    created = await admin_client.post(
        "/api/v1/users",
        json={
            "email": "Nuevo@Deken.test",
            "full_name": "Persona Nueva",
            "role": "editor",
            "password": "Contrasena-Inicial-1",
        },
    )
    assert created.status_code == 201, created.text
    user = created.json()
    assert user["email"] == "nuevo@deken.test"

    duplicate = await admin_client.post(
        "/api/v1/users",
        json={
            "email": "nuevo@deken.test",
            "full_name": "Otra",
            "role": "viewer",
            "password": "Contrasena-Inicial-1",
        },
    )
    assert duplicate.status_code == 409
    weak = await admin_client.post(
        "/api/v1/users",
        json={"email": "d@deken.test", "full_name": "D", "role": "viewer", "password": "123"},
    )
    assert weak.status_code == 422

    changed = await admin_client.patch(f"/api/v1/users/{user['id']}", json={"role": "reviewer"})
    assert changed.status_code == 200
    assert changed.json()["role"] == "reviewer"

    audit = (await admin_client.get("/api/v1/audit", params={"limit": 50})).json()["items"]
    actions = [e["action"] for e in audit]
    assert "user.create" in actions
    role_change = next(e for e in audit if e["action"] == "user.role_change")
    assert role_change["details"]["role"] == {"from": "editor", "to": "reviewer"}
    assert role_change["target_id"] == user["id"]


async def test_last_admin_cannot_be_removed(admin_client: ApiClient) -> None:
    me = (await admin_client.get("/api/v1/auth/me")).json()["user"]
    response = await admin_client.patch(f"/api/v1/users/{me['id']}", json={"role": "viewer"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "last_admin"
    response = await admin_client.patch(f"/api/v1/users/{me['id']}", json={"is_active": False})
    assert response.status_code == 409


async def test_worker_registration_and_revocation_are_audited(admin_client: ApiClient) -> None:
    created = await admin_client.post(
        "/api/v1/workers", json={"name": "Equipo WSL2", "queues": ["render"]}
    )
    assert created.status_code == 201
    body = created.json()
    assert body["token"].startswith("dkw_")
    assert body["worker"]["token_prefix"] == body["token"][4:12]
    listed = (await admin_client.get("/api/v1/workers")).json()
    assert "token" not in listed[0]
    assert "token_hash" not in listed[0]

    revoked = await admin_client.post(f"/api/v1/workers/{body['worker']['id']}/revoke")
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"

    actions = [e["action"] for e in (await admin_client.get("/api/v1/audit")).json()["items"]]
    assert "worker.register" in actions
    assert "worker.revoke" in actions


async def test_audit_log_is_append_only(admin_client: ApiClient, ctx: AppContext) -> None:
    async with ctx.engine.connect() as conn:
        with pytest.raises(DBAPIError, match="solo inserción"):
            await conn.execute(text("UPDATE audit_events SET action = 'x'"))
        await conn.rollback()
        with pytest.raises(DBAPIError, match="solo inserción"):
            await conn.execute(text("DELETE FROM audit_events"))
