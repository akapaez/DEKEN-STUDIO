from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import select

from deken_api.api.v1.schemas import AuditEventOut, AuditListOut
from deken_api.db.models import AuditEvent
from deken_api.deps import Db, Principal, require
from deken_api.security.rbac import Permission

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditListOut)
async def list_audit_events(
    db: Db,
    action: str | None = Query(default=None, max_length=64),
    outcome: str | None = Query(default=None, pattern="^(success|failure|denied)$"),
    limit: int = Query(default=50, ge=1, le=200),
    before: int | None = Query(default=None, ge=1),
    _: Principal = require(Permission.AUDIT_READ),
) -> AuditListOut:
    stmt = select(AuditEvent)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    if outcome:
        stmt = stmt.where(AuditEvent.outcome == outcome)
    if before:
        stmt = stmt.where(AuditEvent.id < before)
    stmt = stmt.order_by(AuditEvent.id.desc()).limit(limit)
    events = list((await db.execute(stmt)).scalars())
    return AuditListOut(
        items=[AuditEventOut.model_validate(e) for e in events],
        next_before=events[-1].id if len(events) == limit else None,
    )
