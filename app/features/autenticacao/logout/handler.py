from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.autenticacao.models import RefreshTokenSession
from app.shared.security.tokens import gerar_hash_token


class LogoutHandler:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def executar(self, refresh_token: str | None) -> None:
        """
        Orquestra a invalidação lógica da sessão de refresh token.
        """
        if not refresh_token:
            return

        token_hash = gerar_hash_token(refresh_token)

        result = await self.db.execute(
            select(RefreshTokenSession).where(
                RefreshTokenSession.token_hash == token_hash
            )
        )
        sessao = result.scalar_one_or_none()

        if sessao:
            sessao.revogado = True
            await self.db.commit()
