"""S0-04, S0-06, S0-07: autenticación, sesiones, CSRF, origen y limitación de intentos."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update

from deken_api.context import AppContext
from deken_api.db.models import AuditEvent, UserSession
from deken_api.security.rbac import Role
from deken_api.security.tokens import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE
from deken_api.testing import ORIGIN, TEST_PASSWORD, ApiClient, ClientFactory, UserFactory

pytestmark = pytest.mark.integration


async def test_login_sets_secure_cookies_and_me(
    client_factory: ClientFactory, make_user: UserFactory
) -> None:
    user = await make_user(Role.EDITOR)
    client = await client_factory()
    response = await client.login(user.email)
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == user.email
    assert "jobs:manage" in body["permissions"]
    assert "users:manage" not in body["permissions"]
    set_cookie = response.headers.get_list("set-cookie")
    session_cookie = next(c for c in set_cookie if c.startswith(f"{SESSION_COOKIE}="))
    assert "HttpOnly" in session_cookie
    assert "samesite=lax" in session_cookie.lower()
    csrf_cookie = next(c for c in set_cookie if c.startswith(f"{CSRF_COOKIE}="))
    assert "HttpOnly" not in csrf_cookie

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["id"] == str(user.id)
    assert me.json()["csrf_token"] == body["csrf_token"]


async def test_login_email_is_case_insensitive(
    client_factory: ClientFactory, make_user: UserFactory
) -> None:
    user = await make_user(Role.VIEWER)
    client = await client_factory()
    assert (await client.login(user.email.upper())).status_code == 200


@pytest.mark.parametrize("variant", ["bad_password", "unknown_user"])
async def test_login_failure_is_generic_and_audited(
    variant: str, client_factory: ClientFactory, make_user: UserFactory, ctx: AppContext
) -> None:
    user = await make_user(Role.VIEWER)
    client = await client_factory()
    email = user.email if variant == "bad_password" else "nadie@deken.test"
    response = await client.login(email, "contraseña-incorrecta")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"
    assert response.json()["error"]["message"] == "Email o contraseña incorrectos"
    async with ctx.sessionmaker() as db:
        event = (
            await db.execute(
                select(AuditEvent).where(
                    AuditEvent.action == "auth.login", AuditEvent.outcome == "failure"
                )
            )
        ).scalar_one()
    assert event.details["reason"] == variant


async def test_unauthenticated_requests_are_rejected(client_factory: ClientFactory) -> None:
    client = await client_factory()
    for path in ("/api/v1/auth/me", "/api/v1/system/status", "/api/v1/jobs"):
        response = await client.get(path)
        assert response.status_code == 401, path
        assert response.json()["error"]["code"] == "not_authenticated"


async def test_logout_revokes_session(
    client_factory: ClientFactory, make_user: UserFactory
) -> None:
    user = await make_user(Role.VIEWER)
    client = await client_factory()
    await client.login(user.email)
    stolen_cookie = client.cookies.get(SESSION_COOKIE)
    assert (await client.post("/api/v1/auth/logout", headers={"Origin": ORIGIN})).status_code == 204
    # Reutilizar la cookie anterior no sirve: la sesión está revocada en servidor.
    other = await client_factory()
    other.cookies.set(SESSION_COOKIE, stolen_cookie or "")
    assert (await other.get("/api/v1/auth/me")).status_code == 401


async def test_expired_and_idle_sessions_are_rejected(
    client_factory: ClientFactory, make_user: UserFactory, ctx: AppContext
) -> None:
    user = await make_user(Role.VIEWER)
    client = await client_factory()
    await client.login(user.email)
    async with ctx.sessionmaker() as db:
        await db.execute(
            update(UserSession)
            .where(UserSession.user_id == user.id)
            .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        await db.commit()
    assert (await client.get("/api/v1/auth/me")).status_code == 401

    await client.login(user.email)
    idle = timedelta(minutes=ctx.settings.session_idle_minutes + 1)
    async with ctx.sessionmaker() as db:
        await db.execute(
            update(UserSession)
            .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
            .values(last_seen_at=datetime.now(UTC) - idle)
        )
        await db.commit()
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_deactivated_user_loses_access_immediately(
    admin_client: ApiClient, client_factory: ClientFactory, make_user: UserFactory
) -> None:
    user = await make_user(Role.EDITOR)
    client = await client_factory()
    await client.login(user.email)
    assert (await client.get("/api/v1/auth/me")).status_code == 200
    response = await admin_client.patch(f"/api/v1/users/{user.id}", json={"is_active": False})
    assert response.status_code == 200
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    assert (await client.login(user.email)).status_code == 401


async def test_csrf_token_required_for_unsafe_methods(
    client_factory: ClientFactory, make_user: UserFactory
) -> None:
    user = await make_user(Role.ADMIN)
    client = await client_factory()
    await client.login(user.email)
    token = client.headers.pop(CSRF_HEADER)

    missing = await client.post("/api/v1/system/selftest", json={})
    assert missing.status_code == 403
    assert missing.json()["error"]["code"] == "csrf_failed"

    wrong = await client.post("/api/v1/system/selftest", json={}, headers={CSRF_HEADER: "0" * 64})
    assert wrong.status_code == 403

    bad_origin = await client.post(
        "/api/v1/system/selftest",
        json={},
        headers={CSRF_HEADER: token, "Origin": "https://evil.example"},
    )
    assert bad_origin.status_code == 403
    assert bad_origin.json()["error"]["code"] == "origin_not_allowed"

    ok = await client.post(
        "/api/v1/system/selftest", json={}, headers={CSRF_HEADER: token, "Origin": ORIGIN}
    )
    assert ok.status_code == 201


async def test_login_rejects_foreign_origin(
    client_factory: ClientFactory, make_user: UserFactory
) -> None:
    user = await make_user(Role.VIEWER)
    client = await client_factory()
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": TEST_PASSWORD},
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 403


async def test_login_rate_limit(
    client_factory: ClientFactory, make_user: UserFactory, ctx: AppContext
) -> None:
    user = await make_user(Role.VIEWER)
    client = await client_factory()
    limit = ctx.settings.login_max_per_email
    for _ in range(limit):
        assert (await client.login(user.email, "mal")).status_code == 401
    blocked = await client.login(user.email)
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0
    async with ctx.sessionmaker() as db:
        denied = (
            await db.execute(
                select(AuditEvent).where(
                    AuditEvent.action == "auth.login", AuditEvent.outcome == "denied"
                )
            )
        ).scalar_one()
    assert denied.details == {"reason": "rate_limited"}


async def test_password_change_revokes_other_sessions(
    client_factory: ClientFactory, make_user: UserFactory
) -> None:
    user = await make_user(Role.EDITOR)
    first, second = await client_factory(), await client_factory()
    await first.login(user.email)
    await second.login(user.email)
    new_password = "Nueva-Contrasena-Segura-77"
    weak = await first.post(
        "/api/v1/auth/password",
        json={"current_password": TEST_PASSWORD, "new_password": "corta"},
    )
    assert weak.status_code == 422
    response = await first.post(
        "/api/v1/auth/password",
        json={"current_password": TEST_PASSWORD, "new_password": new_password},
    )
    assert response.status_code == 204
    assert (await first.get("/api/v1/auth/me")).status_code == 200
    assert (await second.get("/api/v1/auth/me")).status_code == 401
    assert (await second.login(user.email, new_password)).status_code == 200
