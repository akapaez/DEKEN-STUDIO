"""Autenticación de usuarios con sesiones de servidor."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from deken_api.config import Settings
from deken_api.db.models import User, UserSession
from deken_api.errors import ApiError, RateLimited
from deken_api.security.passwords import (
    PasswordPolicyError,
    hash_password,
    needs_rehash,
    validate_password,
    verify_password,
)
from deken_api.security.rate_limit import RateLimiter
from deken_api.security.tokens import hash_token, new_session_token
from deken_api.services import audit
from deken_api.services.audit import Actor, AuditContext, RequestMeta

LAST_SEEN_RESOLUTION = timedelta(seconds=60)


class InvalidCredentials(ApiError):
    status_code = 401
    code = "invalid_credentials"


@dataclass(frozen=True)
class LoginResult:
    user: User
    session: UserSession
    token: str


def user_actor(user: User) -> Actor:
    return Actor(type="user", id=user.id, label=user.email)


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s.]+$")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_email(email: str) -> str:
    """Validación sintáctica simple (admite dominios internos como .local)."""
    normalized = normalize_email(email)
    if len(normalized) > 320 or not _EMAIL_RE.fullmatch(normalized):
        raise ValueError("Email no válido")
    return normalized


async def login(
    db: AsyncSession,
    *,
    settings: Settings,
    limiter: RateLimiter,
    email: str,
    password: str,
    meta: RequestMeta,
) -> LoginResult:
    email_n = normalize_email(email)
    anon = AuditContext(Actor.anonymous(email_n), meta)

    by_email = await limiter.hit(
        f"login:email:{email_n}",
        limit=settings.login_max_per_email,
        window_seconds=settings.login_window_seconds,
    )
    by_ip = await limiter.hit(
        f"login:ip:{meta.ip or 'unknown'}",
        limit=settings.login_max_per_ip,
        window_seconds=settings.login_window_seconds,
    )
    if not (by_email.allowed and by_ip.allowed):
        retry = max(by_email.retry_after, by_ip.retry_after)
        audit.record(db, anon, "auth.login", outcome="denied", details={"reason": "rate_limited"})
        await db.commit()
        raise RateLimited(
            "Demasiados intentos. Inténtalo más tarde.",
            headers={"Retry-After": str(retry)},
        )

    user = (await db.execute(select(User).where(User.email == email_n))).scalar_one_or_none()
    valid = verify_password(user.password_hash if user else None, password)
    if user is None or not valid or not user.is_active:
        reason = "unknown_user" if user is None else ("inactive" if valid else "bad_password")
        audit.record(
            db,
            anon if user is None else AuditContext(user_actor(user), meta),
            "auth.login",
            outcome="failure",
            target_type="user",
            target_id=user.id if user else None,
            details={"reason": reason},
        )
        await db.commit()
        raise InvalidCredentials("Email o contraseña incorrectos")

    now = datetime.now(UTC)
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    token = new_session_token()
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=now + timedelta(hours=settings.session_absolute_hours),
        last_seen_at=now,
        ip=meta.ip,
        user_agent=(meta.user_agent or "")[:400] or None,
    )
    db.add(session)
    user.last_login_at = now
    audit.record(
        db,
        AuditContext(user_actor(user), meta),
        "auth.login",
        target_type="user",
        target_id=user.id,
    )
    await db.commit()
    await limiter.reset(f"login:email:{email_n}")
    session.user = user
    return LoginResult(user=user, session=session, token=token)


async def resolve_session(
    db: AsyncSession, token: str, *, settings: Settings
) -> UserSession | None:
    """Sesión válida para el token, o None. Actualiza `last_seen_at` con baja frecuencia."""
    now = datetime.now(UTC)
    idle_limit = now - timedelta(minutes=settings.session_idle_minutes)
    session = (
        await db.execute(
            select(UserSession).where(
                UserSession.token_hash == hash_token(token),
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
                UserSession.last_seen_at > idle_limit,
            )
        )
    ).scalar_one_or_none()
    if session is None or not session.user.is_active:
        return None
    if now - session.last_seen_at > LAST_SEEN_RESOLUTION:
        session.last_seen_at = now
        await db.commit()
    return session


async def logout(db: AsyncSession, session: UserSession, meta: RequestMeta) -> None:
    session.revoked_at = datetime.now(UTC)
    session.revoked_reason = "logout"
    audit.record(
        db,
        AuditContext(user_actor(session.user), meta),
        "auth.logout",
        target_type="session",
        target_id=session.id,
    )
    await db.commit()


async def revoke_user_sessions(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    reason: str,
    except_session_id: uuid.UUID | None = None,
) -> None:
    stmt = (
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC), revoked_reason=reason)
    )
    if except_session_id is not None:
        stmt = stmt.where(UserSession.id != except_session_id)
    await db.execute(stmt)


async def change_password(
    db: AsyncSession,
    session: UserSession,
    *,
    current_password: str,
    new_password: str,
    meta: RequestMeta,
) -> None:
    user = session.user
    ctx = AuditContext(user_actor(user), meta)
    if not verify_password(user.password_hash, current_password):
        audit.record(
            db, ctx, "auth.password_change", outcome="failure", details={"reason": "bad_password"}
        )
        await db.commit()
        raise InvalidCredentials("La contraseña actual no es correcta")
    try:
        validate_password(new_password, email=user.email)
    except PasswordPolicyError as exc:
        raise ApiError(str(exc), code="weak_password", status_code=422) from exc
    if verify_password(user.password_hash, new_password):
        raise ApiError(
            "La nueva contraseña debe ser distinta de la actual",
            code="weak_password",
            status_code=422,
        )
    user.password_hash = hash_password(new_password)
    user.password_changed_at = datetime.now(UTC)
    await revoke_user_sessions(db, user.id, reason="password_changed", except_session_id=session.id)
    audit.record(db, ctx, "auth.password_change", target_type="user", target_id=user.id)
    await db.commit()
