from uuid import UUID
from fastapi import APIRouter, Depends, Response, Cookie
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import obter_usuario_atual
from app.shared.security.tokens import gerar_hash_token

from app.features.autenticacao.models import RefreshTokenSession
from app.shared.security.schemas import UsuarioToken

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/logout")
async def logout(
    response: Response,
    usuario_atual: UsuarioToken = Depends(obter_usuario_atual),
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if refresh_token:
        token_hash = gerar_hash_token(refresh_token)

        result = await db.execute(
            select(RefreshTokenSession).where(
                RefreshTokenSession.token_hash == token_hash
            )
        )

        sessao = result.scalar_one_or_none()

        if sessao:
            sessao.revogado = True
            await db.commit()

    response.delete_cookie(
        key="refresh_token",
        path="/auth/refresh",
    )

    return {"message": "Logout realizado com sucesso."}
