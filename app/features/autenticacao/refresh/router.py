from typing import Annotated
from fastapi import APIRouter, Cookie, Depends, Request, Response, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.rate_limiter import limiter, get_user_rate_limit_key
from app.config import settings

from app.features.autenticacao.refresh.schemas import TokenResponse
from app.features.autenticacao.refresh.handler import RefreshHandler

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute", key_func=get_user_rate_limit_key)
async def refresh_token(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: Annotated[str | None, Cookie()] = None,
):
    """
    Renova o Access Token do operador utilizando o Refresh Token rotacionado.
    Não exige cabeçalho de autorização padrão, mantendo consistência REST.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cookie de Refresh Token não fornecido.",
        )

    # Executa a regra de negócio e rotação de credenciais
    handler = RefreshHandler(db)
    novo_access, novo_refresh, expiracao_seconds = await handler.executar(refresh_token)

    # Grava o novo refresh token rotacionado em Cookie HttpOnly com Path Restrict!
    response.set_cookie(
        key="refresh_token",
        value=novo_refresh,
        httponly=True,
        secure=getattr(settings, "IS_PRODUCTION", False),
        samesite="lax",
        max_age=28800,  # 8 horas
        path="/auth/refresh",
    )

    return TokenResponse(
        access_token=novo_access,
        token_type="bearer",
        expires_in_seconds=expiracao_seconds,
    )
