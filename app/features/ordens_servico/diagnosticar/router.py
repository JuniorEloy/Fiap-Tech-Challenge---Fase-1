from typing import Annotated, List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles, obter_usuario_atual
from app.shared.security.roles import Role
from app.shared.security.schemas import UsuarioToken

from app.features.ordens_servico.models import OrdemServico, StatusOS
from app.features.ordens_servico.diagnosticar.handler import LancarDiagnosticoHandler
from app.features.ordens_servico.diagnosticar.schemas import (
    LancarDiagnosticoRequest,
    OrdemServicoResponse,
)

router = APIRouter(prefix="/ordens-servico", tags=["Gestão de Ordens de Serviço"])


@router.put(
    "/{id}/diagnostico",
    response_model=OrdemServicoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requer_roles([Role.MECANICO, Role.GERENTE]))],
)
async def lancar_diagnostico_tecnico(
    id: UUID,
    payload: LancarDiagnosticoRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    operador_atual: Annotated[UsuarioToken, Depends(obter_usuario_atual)],
):
    """
    Registra os resultados físicos do diagnóstico técnico de um veículo sob avaliação.
    Insere a lista final de serviços e peças necessários com congelamento de preços.
    A OS é transicionada para 'AGUARDANDO_APROVACAO' (notificação enviada ao cliente).
    Acesso autorizado apenas para MECÂNICO ou GERENTE.
    """
    handler = LancarDiagnosticoHandler(db)
    return await handler.executar(
        os_id=id, command=payload, mecanico_id=operador_atual.id
    )


@router.get(
    "/mecanico/minhas-os",
    response_model=List[OrdemServicoResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requer_roles([Role.MECANICO]))],
)
async def listar_minhas_ordens_de_servico_ativas(
    db: Annotated[AsyncSession, Depends(get_db)],
    operador_atual: Annotated[UsuarioToken, Depends(obter_usuario_atual)],
):
    """
    Retorna a fila de trabalho ativa (pátio de manutenção) do mecânico autenticado.
    Lista apenas Ordens de Serviço sob sua responsabilidade nos status:
    - 'EM_DIAGNOSTICO' (Aguardando laudo técnico)
    - 'EM_EXECUCAO' (Em andamento/manutenção ativa)
    """
    query = (
        select(OrdemServico)
        .where(OrdemServico.mecanico_id == operador_atual.id)
        .where(OrdemServico.status.in_([StatusOS.EM_DIAGNOSTICO, StatusOS.EM_EXECUCAO]))
        .order_by(OrdemServico.data_abertura.asc())
    )

    result = await db.execute(query)
    ordens = result.scalars().all()
    return [OrdemServicoResponse.model_validate(os) for os in ordens]
