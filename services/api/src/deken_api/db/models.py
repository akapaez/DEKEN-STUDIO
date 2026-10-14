"""Modelo de datos de Sprint 0.

Ver docs/DATA_MODEL.md para la descripción completa y la evolución por sprint.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from deken_api.db.base import Base, check_in, created_at_col, updated_at_col, uuid_pk
from deken_api.security.rbac import Role
from deken_shared.jobs import JobStatus

ROLE_VALUES = [r.value for r in Role]
JOB_STATUS_VALUES = [s.value for s in JobStatus]
OBJECT_KINDS = ["original", "derived", "render", "brand", "system_test"]
OBJECT_STATUSES = ["pending", "available", "rejected", "deleted"]
WORKER_STATUSES = ["active", "revoked"]
ACTOR_TYPES = ["user", "worker", "system", "anonymous"]
OUTCOMES = ["success", "failure", "denied"]


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(check_in("role", ROLE_VALUES), name="role_valid"),
        CheckConstraint("email = lower(email)", name="email_lowercase"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()
    last_login_at: Mapped[datetime | None]
    password_changed_at: Mapped[datetime | None]


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = created_at_col()
    last_seen_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    revoked_reason: Mapped[str | None] = mapped_column(String(64))
    ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(400))

    user: Mapped[User] = relationship(lazy="joined")


class AuditEvent(Base):
    """Registro de auditoría. La aplicación solo inserta; nunca actualiza ni borra."""

    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint(check_in("actor_type", ACTOR_TYPES), name="actor_type_valid"),
        CheckConstraint(check_in("outcome", OUTCOMES), name="outcome_valid"),
        Index("ix_audit_events_occurred_at", "occurred_at"),
        Index("ix_audit_events_action", "action"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    occurred_at: Mapped[datetime] = created_at_col()
    actor_type: Mapped[str] = mapped_column(String(16))
    actor_id: Mapped[uuid.UUID | None]
    actor_label: Mapped[str | None] = mapped_column(String(320))
    action: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(16))
    target_type: Mapped[str | None] = mapped_column(String(32))
    target_id: Mapped[str | None] = mapped_column(String(64))
    ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(400))
    request_id: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))


class Worker(Base):
    __tablename__ = "workers"
    __table_args__ = (CheckConstraint(check_in("status", WORKER_STATUSES), name="status_valid"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(100), unique=True)
    token_prefix: Mapped[str] = mapped_column(String(16))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(16), server_default=text("'active'"))
    queues: Mapped[list[str]] = mapped_column(ARRAY(String(32)))
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    version: Mapped[str | None] = mapped_column(String(50))
    hostname: Mapped[str | None] = mapped_column(String(255))
    platform: Mapped[str | None] = mapped_column(String(255))
    last_seen_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = created_at_col()
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    revoked_at: Mapped[datetime | None]


class StoredObject(Base):
    """Objeto en el almacenamiento S3. La clave la genera siempre el servidor."""

    __tablename__ = "stored_objects"
    __table_args__ = (
        CheckConstraint(check_in("kind", OBJECT_KINDS), name="kind_valid"),
        CheckConstraint(check_in("status", OBJECT_STATUSES), name="status_valid"),
        UniqueConstraint("bucket", "key", name="uq_stored_objects_bucket_key"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    bucket: Mapped[str] = mapped_column(String(63))
    key: Mapped[str] = mapped_column(String(512))
    kind: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), server_default=text("'pending'"))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(String(64))
    original_filename: Mapped[str | None] = mapped_column(String(255))
    media_info: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at_col()
    verified_at: Mapped[datetime | None]
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_by_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), index=True
    )


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(check_in("status", JOB_STATUS_VALUES), name="status_valid"),
        CheckConstraint("progress >= 0 AND progress <= 1", name="progress_range"),
        CheckConstraint("attempts >= 0 AND max_attempts >= 1", name="attempts_valid"),
        Index(
            "ix_jobs_claimable",
            "queue",
            "priority",
            "created_at",
            postgresql_where=text("status = 'queued'"),
        ),
        Index(
            "ix_jobs_lease",
            "lease_expires_at",
            postgresql_where=text("status = 'processing'"),
        ),
        Index("ix_jobs_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    type: Mapped[str] = mapped_column(String(64))
    queue: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), server_default=text("'queued'"))
    priority: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    progress: Mapped[float] = mapped_column(Float, server_default=text("0"))
    progress_message: Mapped[str | None] = mapped_column(String(500))
    attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    max_attempts: Mapped[int] = mapped_column(Integer, server_default=text("3"))
    timeout_s: Mapped[int] = mapped_column(Integer, server_default=text("3600"))
    run_after: Mapped[datetime] = mapped_column(server_default=func.now())
    lease_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workers.id", ondelete="SET NULL")
    )
    lease_expires_at: Mapped[datetime | None]
    cancel_requested: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    contract_version: Mapped[int] = mapped_column(Integer)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]


class JobEvent(Base):
    __tablename__ = "job_events"
    __table_args__ = (Index("ix_job_events_job_id_id", "job_id", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    occurred_at: Mapped[datetime] = created_at_col()
    kind: Mapped[str] = mapped_column(String(32))
    attempt: Mapped[int] = mapped_column(Integer)
    message: Mapped[str | None] = mapped_column(Text)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))


class JobOutput(Base):
    __tablename__ = "job_outputs"
    __table_args__ = (
        UniqueConstraint("job_id", "attempt", "name", name="uq_job_outputs_job_attempt_name"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    attempt: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(16))
    object_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stored_objects.id", ondelete="RESTRICT")
    )
    verified: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    verification: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at_col()

    stored_object: Mapped[StoredObject] = relationship(lazy="joined")
