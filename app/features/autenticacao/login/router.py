from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.shared.infra.db.database import get_db
from app.shared.security.rate_limiter import limiter, get_login_rate_limit_key
from app.config import settings

from app.features.autenticacao.login.schemas import LoginRequest, TokenResponse
from app.features.autenticacao.login.handler import LoginHandler

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute", key_func=get_login_rate_limit_key)
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Realiza o login de operadores da oficina.
    O Refresh Token é retornado via Cookie seguro HttpOnly.
    """
    # 1. Executa o caso de uso no Handler
    handler = LoginHandler(db)
    _, access_token, token_bruto = await handler.executar(body.email, body.senha)

    # 2. Grava o Refresh Token em Cookie HttpOnly
    response.set_cookie(
        key="refresh_token",
        value=token_bruto,
        httponly=True,
        secure=getattr(settings, "IS_PRODUCTION", False),
        samesite="lax",
        max_age=28800,  # 8 horas
        path="/auth/refresh",
    )

    # 3. ⏱️ Calcula a expiração do Token para a resposta do JSON
    expires_in_minutes = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 15)
    expires_in_seconds = expires_in_minutes * 60

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_seconds=expires_in_seconds,
    )
