from datetime import timedelta
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.features.autenticacao.models import RefreshTokenSession
from app.features.usuarios.models import Usuario
from app.shared.utils.clock import DateTimeProvider

from app.shared.security.tokens import (
    criar_access_token,
    criar_refresh_token_bruto,
    gerar_hash_token,
)

MSG_SESSAO_INVALIDA = "Sessão de refresh inválida, expirada ou revogada."


class RefreshHandler:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.clock = DateTimeProvider()

    async def _buscar_sessao(self, raw_refresh_token: str) -> RefreshTokenSession:
        token_hash = gerar_hash_token(raw_refresh_token)
        stmt = select(RefreshTokenSession).where(
            RefreshTokenSession.token_hash == token_hash
        )
        result = await self.db.execute(stmt)
        sessao = result.scalar_one_or_none()

        if not sessao:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=MSG_SESSAO_INVALIDA,
                headers={"WWW-Authenticate": "Bearer"},
            )
        return sessao

    def _validar_expiracao(self, sessao: RefreshTokenSession) -> None:
        agora = self.clock.agora()
        agora_naive = agora.replace(tzinfo=None) if agora.tzinfo else agora

        limite_tempo = sessao.expira_em if sessao.expira_em else agora_naive
        limite_naive = (
            limite_tempo.replace(tzinfo=None) if limite_tempo.tzinfo else limite_tempo
        )

        if limite_naive < agora_naive:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=MSG_SESSAO_INVALIDA,
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def _tratar_sessao_revogada(self, sessao: RefreshTokenSession) -> None:
        if not sessao.revogado:
            return

        criado_em = getattr(sessao, "created_at", getattr(sessao, "data_criacao", None))
        criado_em_naive = (
            criado_em.replace(tzinfo=None)
            if criado_em and criado_em.tzinfo
            else criado_em
        )

        fora_da_janela = True
        if criado_em_naive:
            tempo_decorrido = self.clock.agora() - criado_em_naive
            fora_da_janela = tempo_decorrido > timedelta(seconds=10)

        if fora_da_janela:
            stmt_invalidar = (
                update(RefreshTokenSession)
                .where(
                    RefreshTokenSession.usuario_id == sessao.usuario_id,
                    RefreshTokenSession.revogado == False,
                )
                .values(revogado=True)
            )
            await self.db.execute(stmt_invalidar)
            await self.db.commit()

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sessão de refresh inválida, expirada ou revogada. Detectada tentativa de reuso (violação de segurança).",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=MSG_SESSAO_INVALIDA,
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def _buscar_usuario_ativo(self, usuario_id: UUID) -> Usuario:
        stmt_usuario = select(Usuario).where(Usuario.id == usuario_id)
        res_usuario = await self.db.execute(stmt_usuario)
        usuario = res_usuario.scalar_one_or_none()

        if not usuario or not usuario.ativo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Operador inativo ou não cadastrado no sistema.",
            )
        return usuario

    async def executar(self, raw_refresh_token: str) -> tuple[str, str, int]:
        """
        Executa a rotação de refresh token (RTR):
        1. Calcula o hash SHA-256 do token bruto apresentado.
        2. Localiza a sessão correspondente ativa no banco.
        3. Valida expiração e estado de revogação.
        4. Revoga o token atual e gera um novo par rotacionado.
        5. Retorna o (novo_access_token, novo_raw_refresh, expiracao_segundos).
        """
        # 1 e 2. Busca e valida integridade básica da sessão
        sessao = await self._buscar_sessao(raw_refresh_token)

        # Validação de expiração temporal
        self._validar_expiracao(sessao)

        # Tratamento de detecção de reuso / violação RTR
        await self._tratar_sessao_revogada(sessao)

        # 3. Busca operador associado para herdar permissões e role
        usuario = await self._buscar_usuario_ativo(sessao.usuario_id)

        # 4. Refresh Token Rotation (RTR): Invalida o token atual
        sessao.revogado = True

        # 5. Gera novos tokens rotacionados
        novo_refresh_bruto, novo_token_hash = criar_refresh_token_bruto()

        tempo_vida_refresh = timedelta(hours=8)
        exp_refresh = self.clock.agora() + tempo_vida_refresh

        nova_sessao = RefreshTokenSession(
            usuario_id=usuario.id,
            token_hash=novo_token_hash,
            expira_em=exp_refresh,
            revogado=False,
        )
        self.db.add(nova_sessao)

        # Gera novo access token temporário
        tempo_vida_access = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 15)

        novo_access_token = criar_access_token(
            usuario_id=usuario.id,
            role=usuario.role,
        )

        # Salva as mudanças de forma atômica
        await self.db.commit()

        expiracao_segundos = tempo_vida_access * 60
        return novo_access_token, novo_refresh_bruto, expiracao_segundos
