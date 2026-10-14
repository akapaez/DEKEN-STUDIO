"""Generación y comprobación de tokens opacos."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from uuid import UUID

SESSION_COOKIE = "deken_session"
CSRF_COOKIE = "deken_csrf"
CSRF_HEADER = "X-CSRF-Token"
WORKER_TOKEN_PREFIX = "dkw_"  # noqa: S105 - prefijo público, no un secreto


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def new_worker_token() -> str:
    return WORKER_TOKEN_PREFIX + secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 hex. Suficiente para tokens de 256 bits aleatorios (no son contraseñas)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def csrf_token_for(session_id: UUID, secret_key: str) -> str:
    mac = hmac.new(secret_key.encode("utf-8"), b"csrf:" + session_id.bytes, hashlib.sha256)
    return mac.hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
