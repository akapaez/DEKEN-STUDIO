from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from deken_api.api.v1.schemas import (
    RoleInfo,
    UserCreateRequest,
    UserOut,
    UserPasswordResetRequest,
    UserUpdateRequest,
)
from deken_api.deps import Db, Principal, require
from deken_api.security.rbac import ROLE_LABELS, ROLE_PERMISSIONS, Permission
from deken_api.services import users as users_service

router = APIRouter(prefix="/users", tags=["users"])

Admin = require(Permission.USERS_MANAGE)


@router.get("/roles", response_model=list[RoleInfo])
async def list_roles(_: Principal = require(Permission.SYSTEM_READ)) -> list[RoleInfo]:
    return [
        RoleInfo(role=role, label=ROLE_LABELS[role], permissions=sorted(perms))
        for role, perms in ROLE_PERMISSIONS.items()
    ]


@router.get("", response_model=list[UserOut])
async def list_users(db: Db, _: Principal = Admin) -> list[UserOut]:
    return [UserOut.model_validate(u) for u in await users_service.list_users(db)]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreateRequest, db: Db, principal: Principal = Admin) -> UserOut:
    user = await users_service.create_user(
        db,
        principal.audit,
        email=body.email,
        full_name=body.full_name,
        role=body.role,
        password=body.password,
    )
    return UserOut.model_validate(user)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID, body: UserUpdateRequest, db: Db, principal: Principal = Admin
) -> UserOut:
    user = await users_service.update_user(
        db,
        principal.audit,
        user_id,
        full_name=body.full_name,
        role=body.role,
        is_active=body.is_active,
    )
    return UserOut.model_validate(user)


@router.post("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    user_id: uuid.UUID, body: UserPasswordResetRequest, db: Db, principal: Principal = Admin
) -> None:
    await users_service.set_password(db, principal.audit, user_id, password=body.password)
