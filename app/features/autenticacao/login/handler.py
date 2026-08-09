from datetime import timedelta
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.autenticacao.models import RefreshTokenSession
from app.features.usuarios.models import Usuario
from app.shared.security.password import verificar_senha
from app.shared.security.tokens import criar_access_token, criar_refresh_token_bruto
from app.shared.utils.clock import DateTimeProvider


class LoginHandler:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def executar(self, email_higienizado: str, senha_crua: str) -> tuple[Usuario, str, str]:
        """
        Executa as validações de credenciais e gera o par de tokens.
        Retorna a tupla (Usuario, AccessToken, RefreshTokenBruto) em caso de sucesso.
        """
        # 1. Busca usuário usando o e-mail que já veio normalizado pelo Schema
        result = await self.db.execute(select(Usuario).where(Usuario.email == email_higienizado))
        usuario = result.scalar_one_or_none()

        # 2. Prevenção de User Enumeration (OWASP A07): Resposta genérica unificada
        if (
            not usuario
            or not verificar_senha(senha_crua, usuario.senha)
            or not usuario.ativo
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas ou conta inativa.",
            )

        # 3. Geração de tokens de forma limpa
        access_token = criar_access_token(usuario.id, usuario.role)
        token_bruto, token_hash = criar_refresh_token_bruto()

        # 4. Registra a sessão do Refresh Token no banco de dados
        sessao = RefreshTokenSession(
            usuario_id=usuario.id,
            token_hash=token_hash,
            expira_em=DateTimeProvider().agora() + timedelta(days=1),
        )
        self.db.add(sessao)
        await self.db.commit()

        return usuario, access_token, token_bruto