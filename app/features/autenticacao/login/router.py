from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.shared.infra.db.database import get_db

from app.shared.security.password import verificar_senha
from app.shared.security.tokens import criar_access_token, criar_refresh_token_bruto
from app.shared.security.rate_limiter import limiter, get_login_rate_limit_key
from app.features.autenticacao.models import RefreshTokenSession
from app.features.usuarios.models import Usuario

from app.shared.utils.clock import DateTimeProvider

router = APIRouter(prefix="/auth", tags=["Autenticação"])


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int = 900  # 15 minutos de validade do Access Token


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute", key_func=get_login_rate_limit_key)
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    # 1. Busca usuário no banco
    result = await db.execute(select(Usuario).where(Usuario.email == body.email))
    usuario = result.scalar_one_or_none()

    # 2. Resposta genérica para evitar User Enumeration (OWASP A07)
    if (
        not usuario
        or not verificar_senha(body.senha, usuario.senha)
        or not usuario.ativo
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas ou conta inativa.",
        )

    # 3. Gera o par de tokens (Access Token curto de 15 min e Refresh Token bruto/hash)
    access_token = criar_access_token(
        usuario.id,
        usuario.role,
    )
    token_bruto, token_hash = criar_refresh_token_bruto()

    # 4. Registra a sessão do Refresh Token no banco com expiração de 24 horas (1 dia)
    sessao = RefreshTokenSession(
        usuario_id=usuario.id,
        token_hash=token_hash,
        expira_em=DateTimeProvider().agora() + timedelta(days=1),
    )
    db.add(sessao)
    await db.commit()

    # 5. 🛡️ Grava o Refresh Token em um Cookie HttpOnly (Proteção contra XSS/OWASP A03)
    response.set_cookie(
        key="refresh_token",
        value=token_bruto,
        httponly=True,  # Bloqueia acesso via JavaScript (XSS)
        secure=getattr(
            settings, "IS_PRODUCTION", False
        ),  # False em dev (HTTP), True em prod (HTTPS)
        samesite="lax",  # Proteção contra ataques CSRF
        max_age=28800,  # 8 horas em segundos
        path="/auth/refresh",  # Envia o cookie apenas para a rota de renovação
    )

    # 6. Retorna apenas o Access Token no JSON da resposta
    return TokenResponse(access_token=access_token)
