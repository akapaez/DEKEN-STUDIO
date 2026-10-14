"""Roles y permisos.

La API es la única autoridad: la interfaz solo usa la lista de permisos para ocultar
acciones que la API rechazaría.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class Permission(StrEnum):
    SYSTEM_READ = "system:read"
    SYSTEM_MANAGE = "system:manage"
    USERS_MANAGE = "users:manage"
    WORKERS_MANAGE = "workers:manage"
    AUDIT_READ = "audit:read"
    JOBS_READ = "jobs:read"
    JOBS_MANAGE = "jobs:manage"
    FILES_READ = "files:read"
    MEDIA_READ = "media:read"
    MEDIA_WRITE = "media:write"
    MEDIA_RIGHTS = "media:rights"
    BRAND_READ = "brand:read"
    BRAND_MANAGE = "brand:manage"
    RENDER_CREATE = "render:create"


_ALL = frozenset(Permission)
_READ = frozenset(
    {
        Permission.SYSTEM_READ,
        Permission.JOBS_READ,
        Permission.FILES_READ,
        Permission.MEDIA_READ,
        Permission.BRAND_READ,
    }
)

ROLE_PERMISSIONS: Mapping[Role, frozenset[Permission]] = {
    Role.ADMIN: _ALL,
    Role.EDITOR: _READ | {Permission.JOBS_MANAGE, Permission.MEDIA_WRITE, Permission.RENDER_CREATE},
    # Los derechos de imagen los valida quien aprueba contenidos.
    Role.REVIEWER: _READ | {Permission.MEDIA_RIGHTS},
    Role.VIEWER: _READ,
}

ROLE_LABELS: Mapping[Role, str] = {
    Role.ADMIN: "Administración",
    Role.EDITOR: "Edición y producción",
    Role.REVIEWER: "Revisión y aprobación",
    Role.VIEWER: "Solo lectura",
}


def permissions_for(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[role]


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS[role]
