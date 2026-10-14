from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from deken_api.api.v1.schemas import LoginRequest, MeOut, PasswordChangeRequest, UserOut
from deken_api.deps import (
    Ctx,
    CurrentPrincipal,
    Db,
    Meta,
    Principal,
    check_origin,
    clear_session_cookies,
    set_session_cookies,
)
from deken_api.security.rbac import Role, permissions_for
from deken_api.security.tokens import csrf_token_for
from deken_api.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _me(principal: Principal, csrf: str) -> MeOut:
    return MeOut(
        user=UserOut.model_validate(principal.user),
        permissions=sorted(principal.permissions),
        session_expires_at=principal.session.expires_at,
        csrf_token=csrf,
    )


@router.post("/login", response_model=MeOut)
async def login(
    body: LoginRequest, request: Request, response: Response, db: Db, ctx: Ctx, meta: Meta
) -> MeOut:
    check_origin(request, ctx.settings)
    result = await auth_service.login(
        db,
        settings=ctx.settings,
        limiter=ctx.rate_limiter,
        email=body.email,
        password=body.password,
        meta=meta,
    )
    csrf = set_session_cookies(
        response, token=result.token, session=result.session, settings=ctx.settings
    )
    role = Role(result.user.role)
    return MeOut(
        user=UserOut.model_validate(result.user),
        permissions=sorted(permissions_for(role)),
        session_expires_at=result.session.expires_at,
        csrf_token=csrf,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(principal: CurrentPrincipal, response: Response, db: Db, ctx: Ctx) -> None:
    await auth_service.logout(db, principal.session, principal.meta)
    clear_session_cookies(response, ctx.settings)


@router.get("/me", response_model=MeOut)
async def me(principal: CurrentPrincipal, ctx: Ctx) -> MeOut:
    csrf = csrf_token_for(principal.session.id, ctx.settings.secret_key.get_secret_value())
    return _me(principal, csrf)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(body: PasswordChangeRequest, principal: CurrentPrincipal, db: Db) -> None:
    await auth_service.change_password(
        db,
        principal.session,
        current_password=body.current_password,
        new_password=body.new_password,
        meta=principal.meta,
    )
