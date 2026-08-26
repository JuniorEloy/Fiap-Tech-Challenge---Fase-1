from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role

from app.features.servicos.repository import ServicosRepository
from app.features.servicos.cadastrar_servico.handler import CadastrarServicoHandler
from app.features.servicos.cadastrar_servico.schemas import (
    CadastrarServicoRequest,
    ServicoResponse,
)

router = APIRouter(prefix="/servicos", tags=["Gestão de Serviços"])


@router.post(
    "",
    response_model=ServicoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requer_roles([Role.RECEPCIONISTA, Role.GERENTE]))],
)
async def cadastrar_servico(
    payload: CadastrarServicoRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Catalogar um novo tipo de serviço (mão de obra) no sistema da oficina.
    Acesso permitido para RECEPCIONISTAS e GERENTES.
    """
    repository = ServicosRepository(db)
    handler = CadastrarServicoHandler(repository)
    return await handler.executar(payload)
