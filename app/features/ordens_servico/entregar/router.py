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

from app.shared.domain.ports.notificacao import EnviadorNotificacaoPort
from app.shared.domain.ports.pagamento import GatewayPagamentoPort
from app.shared.infra.dependencies import (
    obter_notificador_whatsapp,
    obter_gateway_pagamento,
)


router = APIRouter(prefix="/ordens-servico", tags=["Gestão de Ordens de Serviço"])


@router.post(
    "/{id}/entregar",
    response_model=EntregaOSResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requer_roles([Role.RECEPCIONISTA, Role.GERENTE]))],
)
async def entregar_ordem_servico(
    id: UUID,
    payload: RegistrarEntregaRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    gateway_pagamento: Annotated[
        GatewayPagamentoPort, Depends(obter_gateway_pagamento)
    ],
    notificador: Annotated[
        EnviadorNotificacaoPort, Depends(obter_notificador_whatsapp)
    ],
    operador_atual: Annotated[UsuarioToken, Depends(obter_usuario_atual)],
):
    """
    Registra o faturamento de caixa e autoriza a saída física do veículo do pátio.
    Aciona o gateway de pagamentos para cartões e envia notificação via WhatsApp.
    Acesso autorizado para RECEPCIONISTAS ou GERENTES.
    """

    handler = RegistrarEntregaHandler(
        db=db, gateway_pagamento=gateway_pagamento, notificador=notificador
    )
    return await handler.executar(
        os_id=id, command=payload, operador_id=operador_atual.id
    )
