from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles, obter_usuario_atual
from app.shared.security.roles import Role
from app.shared.security.schemas import UsuarioToken

from app.features.ordens_servico.finalizar.handler import FinalizarOrdemServicoHandler
from app.features.ordens_servico.finalizar.schemas import (
    FinalizarOrdemServicoRequest,
    FinalizacaoOSResponse,
)

router = APIRouter(prefix="/ordens-servico", tags=["Gestão de Ordens de Serviço"])


@router.post(
    "/{id}/finalizar",
    response_model=FinalizacaoOSResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requer_roles([Role.MECANICO, Role.GERENTE]))],
)
async def finalizar_ordem_servico(
    id: UUID,
    payload: FinalizarOrdemServicoRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    operador_atual: Annotated[UsuarioToken, Depends(obter_usuario_atual)],
):
    """
    Encerra e finaliza a execução dos serviços técnicos de uma Ordem de Serviço em andamento.
    Muda o status para 'FINALIZADA', registrando os carimbos de conclusão, calculando os leadtimes (KPIs)
    e fechando o faturamento final consolidado.
    Acesso autorizado apenas para MECÂNICO ou GERENTE.
    """
    handler = FinalizarOrdemServicoHandler(db)
    return await handler.executar(
        os_id=id, command=payload, mecanico_id=operador_atual.id
    )
