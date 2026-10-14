"""Gestión de usuarios (solo administradores)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from deken_api.db.models import User
from deken_api.errors import ApiError, Conflict, NotFound
from deken_api.security.passwords import PasswordPolicyError, hash_password, validate_password
from deken_api.security.rbac import Role
from deken_api.services import audit
from deken_api.services.audit import AuditContext
from deken_api.services.auth import revoke_user_sessions, validate_email


def _check_password(password: str, email: str) -> None:
    try:
        validate_password(password, email=email)
    except PasswordPolicyError as exc:
        raise ApiError(str(exc), code="weak_password", status_code=422) from exc


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at))
    return list(result.scalars())


async def get_user(db: AsyncSession, user_id: uuid.UUID, *, for_update: bool = False) -> User:
    stmt = select(User).where(User.id == user_id)
    if for_update:
        stmt = stmt.with_for_update()
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise NotFound("Usuario no encontrado")
    return user


async def create_user(
    db: AsyncSession,
    ctx: AuditContext,
    *,
    email: str,
    full_name: str,
    role: Role,
    password: str,
) -> User:
    try:
        email_n = validate_email(email)
    except ValueError as exc:
        raise ApiError(str(exc), code="invalid_email", status_code=422) from exc
    _check_password(password, email_n)
    exists = await db.scalar(select(func.count()).select_from(User).where(User.email == email_n))
    if exists:
        raise Conflict("Ya existe un usuario con ese email", code="email_taken")
    user = User(
        email=email_n,
        full_name=full_name.strip(),
        role=role.value,
        password_hash=hash_password(password),
        password_changed_at=datetime.now(UTC),
    )
    db.add(user)
    await db.flush()
    audit.record(
        db,
        ctx,
        "user.create",
        target_type="user",
        target_id=user.id,
        details={"email": email_n, "role": role.value},
    )
    await db.commit()
    return user


async def _active_admins(db: AsyncSession) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(User)
        .where(User.role == Role.ADMIN.value, User.is_active.is_(True))
    )
    return int(count or 0)


async def update_user(
    db: AsyncSession,
    ctx: AuditContext,
    user_id: uuid.UUID,
    *,
    full_name: str | None = None,
    role: Role | None = None,
    is_active: bool | None = None,
) -> User:
    user = await get_user(db, user_id, for_update=True)
    changes: dict[str, object] = {}
    removing_admin = (
        user.role == Role.ADMIN.value
        and user.is_active
        and ((role is not None and role is not Role.ADMIN) or is_active is False)
    )
    if removing_admin and await _active_admins(db) <= 1:
        raise Conflict("Debe quedar al menos un administrador activo", code="last_admin")
    if full_name is not None and full_name.strip() != user.full_name:
        changes["full_name"] = {"from": user.full_name, "to": full_name.strip()}
        user.full_name = full_name.strip()
    if role is not None and role.value != user.role:
        changes["role"] = {"from": user.role, "to": role.value}
        user.role = role.value
    if is_active is not None and is_active != user.is_active:
        changes["is_active"] = {"from": user.is_active, "to": is_active}
        user.is_active = is_active
        if not is_active:
            await revoke_user_sessions(db, user.id, reason="user_deactivated")
    if changes:
        action = "user.role_change" if "role" in changes else "user.update"
        audit.record(db, ctx, action, target_type="user", target_id=user.id, details=changes)
    await db.commit()
    return user


async def set_password(
    db: AsyncSession, ctx: AuditContext, user_id: uuid.UUID, *, password: str
) -> None:
    user = await get_user(db, user_id, for_update=True)
    _check_password(password, user.email)
    user.password_hash = hash_password(password)
    user.password_changed_at = datetime.now(UTC)
    await revoke_user_sessions(db, user.id, reason="password_reset_by_admin")
    audit.record(db, ctx, "user.password_reset", target_type="user", target_id=user.id)
    await db.commit()
