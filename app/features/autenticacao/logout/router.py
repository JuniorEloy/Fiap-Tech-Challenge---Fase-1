from typing import Annotated
from fastapi import APIRouter, Depends, Response, Cookie, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import obter_usuario_atual
from app.shared.security.schemas import UsuarioToken

from app.features.autenticacao.logout.handler import LogoutHandler
from app.features.autenticacao.logout.schemas import LogoutResponse

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/logout", response_model=LogoutResponse, status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    usuario_atual: UsuarioToken = Depends(obter_usuario_atual),
    refresh_token: Annotated[str | None, Cookie()] = None,
):
    """
    Invalida a sessão do usuário (se houver Refresh Token ativo)
    e deleta os cookies de segurança da máquina do cliente.
    """
    # 1. Executa a regra de negócio/revogação via Handler
    handler = LogoutHandler(db)
    await handler.executar(refresh_token)

    # 2. Executa a manipulação HTTP de saída
    response.delete_cookie(
        key="refresh_token",
        path="/auth/refresh",
    )

    return LogoutResponse(message="Logout realizado com sucesso.")
