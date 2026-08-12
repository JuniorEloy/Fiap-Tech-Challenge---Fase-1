from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles, obter_usuario_atual
from app.shared.security.roles import Role
from app.shared.security.schemas import UsuarioToken

from app.features.ordens_servico.abertura_os.handler import CriarOrdemServicoHandler
from app.features.ordens_servico.abertura_os.schemas import (
    CriarOrdemServicoRequest,
    OrdemServicoResponse,
)

router = APIRouter(prefix="/ordens-servico", tags=["Gestão de Ordens de Serviço"])


@router.post(
    "",
    response_model=OrdemServicoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requer_roles([Role.RECEPCIONISTA, Role.GERENTE]))],
)
async def criar_ordem_servico(
    payload: CriarOrdemServicoRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    operador_atual: Annotated[UsuarioToken, Depends(obter_usuario_atual)],
):
    """
    Efetua a abertura de uma nova Ordem de Serviço (Check-in).
    Se todos os serviços solicitados forem expressos, a OS pula o diagnóstico
    e entra diretamente no status 'AGUARDANDO_APROVACAO' (Orçamento Expresso).
    Permitido apenas para os papéis: RECEPCIONISTA e GERENTE.
    """
    handler = CriarOrdemServicoHandler(db)
    return await handler.executar(payload, operador_id=operador_atual.id)
