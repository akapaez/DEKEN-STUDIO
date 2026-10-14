"""Auditoría: registro de acciones relevantes para la seguridad y la operación."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from deken_api.db.models import AuditEvent


@dataclass(frozen=True)
class RequestMeta:
    ip: str | None = None
    user_agent: str | None = None
    request_id: str | None = None


@dataclass(frozen=True)
class Actor:
    type: str
    id: uuid.UUID | None = None
    label: str | None = None

    @classmethod
    def anonymous(cls, label: str | None = None) -> Actor:
        return cls(type="anonymous", label=label)

    @classmethod
    def system(cls) -> Actor:
        return cls(type="system", label="system")


@dataclass(frozen=True)
class AuditContext:
    actor: Actor
    meta: RequestMeta = field(default_factory=RequestMeta)


def record(
    db: AsyncSession,
    ctx: AuditContext,
    action: str,
    *,
    outcome: str = "success",
    target_type: str | None = None,
    target_id: str | uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Añade el evento a la transacción en curso (se confirma con la acción)."""
    db.add(
        AuditEvent(
            actor_type=ctx.actor.type,
            actor_id=ctx.actor.id,
            actor_label=ctx.actor.label,
            action=action,
            outcome=outcome,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            ip=ctx.meta.ip,
            user_agent=(ctx.meta.user_agent or "")[:400] or None,
            request_id=ctx.meta.request_id,
            details=details or {},
        )
    )
