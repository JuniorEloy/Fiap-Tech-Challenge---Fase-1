from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles, obter_usuario_atual
from app.shared.security.roles import Role
from app.shared.security.schemas import UsuarioToken

from app.features.ordens_servico.aprovar_orcamento.handler import (
    ResponderOrcamentoHandler,
)
from app.features.ordens_servico.aprovar_orcamento.schemas import (
    ResponderOrcamentoRequest,
    RespostaOrcamentoResponse,
)

router = APIRouter(prefix="/ordens-servico", tags=["Gestão de Ordens de Serviço"])


@router.post(
    "/{id}/resposta",
    response_model=RespostaOrcamentoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(requer_roles([Role.RECEPCIONISTA, Role.GERENTE]))
    ],  # 👈 Operador registrando a resposta do cliente
)
async def registrar_resposta_cliente_operador(
    id: UUID,
    payload: ResponderOrcamentoRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    operador_atual: Annotated[UsuarioToken, Depends(obter_usuario_atual)],
):
    """
    Registra a decisão do cliente (Aprovação ou Rejeição do orçamento) por meio de um operador interno.
    Utilizado quando o cliente responde por telefone, WhatsApp ou presencialmente na recepção.
    Acesso autorizado para RECEPCIONISTA ou GERENTE.
    """
    handler = ResponderOrcamentoHandler(db)
    return await handler.executar(
        os_id=id, command=payload, operador_id=operador_atual.id
    )


@router.post(
    "/publica/{hash}/responder",
    response_model=RespostaOrcamentoResponse,
    status_code=status.HTTP_200_OK,
)
async def responder_orcamento_cliente_portal_publico(
    hash: UUID,
    payload: ResponderOrcamentoRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Permite que o próprio cliente aprove ou rejeite seu orçamento diretamente no portal da oficina,
    utilizando o hash seguro de visualização enviado no SMS ou WhatsApp.
    Este endpoint é público (não exige cabeçalho de autenticação JWT de operador interno).
    """
    handler = ResponderOrcamentoHandler(db)
    return await handler.executar_via_hash(hash_visualizacao=hash, command=payload)
