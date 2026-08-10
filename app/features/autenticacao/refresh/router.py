from datetime import timedelta
from typing import Annotated
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.shared.infra.db.database import get_db
from app.shared.utils.clock import DateTimeProvider

from app.shared.security.tokens import (
    criar_access_token,
    criar_refresh_token_bruto,
    gerar_hash_token,
)
from app.shared.security.rate_limiter import limiter, get_user_rate_limit_key
from app.features.autenticacao.models import RefreshTokenSession
from app.features.usuarios.models import Usuario


router = APIRouter(prefix="/auth", tags=["Autenticação"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute", key_func=get_user_rate_limit_key)
async def refresh_token(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: str | None = Cookie(default=None),
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cookie de Refresh Token não fornecido.",
        )

    token_hash = gerar_hash_token(refresh_token)

    stmt = (
        select(RefreshTokenSession)
        .where(RefreshTokenSession.token_hash == token_hash)
        .with_for_update()
    )

    result = await db.execute(stmt)
    sessao = result.scalar_one_or_none()

    if not sessao:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh Token inválido ou não encontrado.",
        )

    agora = DateTimeProvider().agora()

    if sessao.revogado:
        data_revogacao = sessao.revogado_em or sessao.created_at
        
        # Garante compatibilidade de timezone na comparação de revogação
        if data_revogacao.tzinfo is not None and agora.tzinfo is not None:
            data_revogacao_comp = data_revogacao
            agora_comp = agora
        else:
            data_revogacao_comp = data_revogacao.replace(tzinfo=None)
            agora_comp = agora.replace(tzinfo=None)

        if data_revogacao_comp >= agora_comp - timedelta(seconds=10):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh Token já utilizado.",
            )

        await db.execute(
            update(RefreshTokenSession)
            .where(
                RefreshTokenSession.usuario_id == sessao.usuario_id,
                RefreshTokenSession.revogado == False,
            )
            .values(
                revogado=True,
                revogado_em=agora,
            )
        )

        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Violação de segurança detectada (reuso de token). Faça login novamente.",
        )

    # Normalização segura para evitar conflito de tzinfo (offset-naive vs offset-aware) na expiração
    expira_em_val = sessao.expira_em
    if expira_em_val.tzinfo is not None and agora.tzinfo is not None:
        exp_comp = expira_em_val
        agora_exp_comp = agora
    else:
        exp_comp = expira_em_val.replace(tzinfo=None)
        agora_exp_comp = agora.replace(tzinfo=None)

    if exp_comp < agora_exp_comp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão expirada. Por favor, efetue login novamente.",
        )

    result = await db.execute(select(Usuario).where(Usuario.id == sessao.usuario_id))

    usuario = result.scalar_one_or_none()

    if not usuario or not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário inativo ou não encontrado.",
        )

    sessao.revogado = True
    sessao.revogado_em = agora

    novo_access_token = criar_access_token(
        usuario.id,
        usuario.role,
    )

    novo_token_bruto, novo_token_hash = criar_refresh_token_bruto()

    nova_sessao = RefreshTokenSession(
        usuario_id=usuario.id,
        token_hash=novo_token_hash,
        expira_em=agora + timedelta(hours=8),
    )

    db.add(nova_sessao)

    await db.flush()

    sessao.substituido_por_id = nova_sessao.id

    await db.commit()

    response.set_cookie(
        key="refresh_token",
        value=novo_token_bruto,
        httponly=True,
        secure=getattr(settings, "IS_PRODUCTION", False),
        samesite="lax",
        max_age=28800,
        path="/auth/refresh",
    )

    return TokenResponse(
        access_token=novo_access_token,
    )