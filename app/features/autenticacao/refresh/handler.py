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


class RefreshHandler:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.clock = DateTimeProvider()

    async def executar(self, raw_refresh_token: str) -> tuple[str, str, int]:
        """
        Executa a rotação de refresh token (RTR):
        1. Calcula o hash SHA-256 do token bruto apresentado.
        2. Localiza a sessão correspondente ativa no banco.
        3. Valida expiração e estado de revogação.
        4. Revoga o token atual e gera um novo par rotacionado.
        5. Retorna o (novo_access_token, novo_raw_refresh, expiracao_segundos).
        """
        # 1. Calcula hash do token de entrada
        token_hash = gerar_hash_token(raw_refresh_token)

        # 2. Busca sessão no banco de dados
        stmt = select(RefreshTokenSession).where(
            RefreshTokenSession.token_hash == token_hash
        )
        result = await self.db.execute(stmt)
        sessao = result.scalar_one_or_none()

        # Sessão Inexistente ou Expirada pelo Tempo
        if not sessao or sessao.expira_em < self.clock.agora():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sessão de refresh inválida, expirada ou revogada.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # DETECÇÃO DE VIOLAÇÃO / REUSO (RTR Violation): Se o token apresentado já foi revogado antes
        if sessao.revogado:
            # Recupera o timestamp de criação da sessão (resiliente a 'created_at' ou 'data_criacao')
            criado_em = getattr(
                sessao, "created_at", getattr(sessao, "data_criacao", None)
            )

            # Tolerância padrão de 10 segundos para concorrência de rede do front-end (Grace Period)
            fora_da_janela = True
            if criado_em:
                tempo_decorrido = self.clock.agora() - criado_em
                fora_da_janela = tempo_decorrido > timedelta(seconds=10)

            if fora_da_janela:
                # VIOLAÇÃO DETECTADA (Fora da janela de 10s): Invalidamos todas as outras sessões ativas do usuário
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
                # CONCORRÊNCIA ACEITA (Dentro da janela de 10s): Apenas rejeita a requisição atual
                # mas não revoga as demais sessões do usuário ativo!
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Sessão de refresh inválida, expirada ou revogada.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # Validação de integridade da sessão
        if not sessao or sessao.revogado or sessao.expira_em < self.clock.agora():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sessão de refresh inválida, expirada ou revogada.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 3. Busca operador associado para herdar permissões e role
        stmt_usuario = select(Usuario).where(Usuario.id == sessao.usuario_id)
        res_usuario = await self.db.execute(stmt_usuario)
        usuario = res_usuario.scalar_one_or_none()

        if not usuario or not usuario.ativo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Operador inativo ou não cadastrado no sistema.",
            )

        # 4. Refresh Token Rotation (RTR): Invalida o token atual
        sessao.revogado = True

        # 5. Gera novos tokens rotacionados
        novo_refresh_bruto = criar_refresh_token_bruto()
        novo_token_hash = gerar_hash_token(novo_refresh_bruto)

        # Configura tempo de expiração do novo refresh (ex: 8 horas)
        tempo_vida_refresh = timedelta(hours=8)
        exp_refresh = self.clock.agora() + tempo_vida_refresh

        # Cria nova sessão ativa no banco
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
            expires_delta=timedelta(minutes=tempo_vida_access),
        )

        # Salva as mudanças de forma atômica
        await self.db.commit()

        expiracao_segundos = tempo_vida_access * 60
        return novo_access_token, novo_refresh_bruto, expiracao_segundos
