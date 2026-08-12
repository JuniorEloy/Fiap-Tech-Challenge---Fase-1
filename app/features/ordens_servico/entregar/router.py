from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles, obter_usuario_atual
from app.shared.security.roles import Role
from app.shared.security.schemas import UsuarioToken

from app.features.ordens_servico.entregar.handler import RegistrarEntregaHandler
from app.features.ordens_servico.entregar.schemas import (
    RegistrarEntregaRequest,
    EntregaOSResponse,
)

router = APIRouter(prefix="/ordens-servico", tags=["Gestão de Ordens de Serviço"])


@router.post(
    "/{id}/entregar",
    response_model=EntregaOSResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requer_roles([Role.RECEPCIONISTA, Role.GERENTE]))],
)
async def registrar_entrega_e_pagamento(
    id: UUID,
    payload: RegistrarEntregaRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    operador_atual: Annotated[UsuarioToken, Depends(obter_usuario_atual)],
):
    """
    Registra o recebimento financeiro no caixa (pagamento) e autoriza a entrega final do veículo ao cliente.
    Transiciona a Ordem de Serviço do status 'FINALIZADA' para o status finalizador 'ENTREGUE'.
    Acesso autorizado apenas para RECEPCIONISTA ou GERENTE.
    """
    handler = RegistrarEntregaHandler(db)
    return await handler.executar(
        os_id=id, command=payload, operador_id=operador_atual.id
    )
