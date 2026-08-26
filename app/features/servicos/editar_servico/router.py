from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role

from app.features.servicos.repository import ServicosRepository
from app.features.servicos.editar_servico.handler import EditarServicoHandler
from app.features.servicos.editar_servico.schemas import EditarServicoRequest
from app.features.servicos.schemas import ServicoResponse

router = APIRouter(prefix="/servicos", tags=["Gestão de Serviços"])


@router.put(
    "/{id}",
    response_model=ServicoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requer_roles([Role.RECEPCIONISTA, Role.GERENTE]))],
)
async def editar_servico(
    id: UUID,
    payload: EditarServicoRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Altera características cadastrais, tempos estimados ou precificação de um serviço do catálogo.
    Acesso permitido exclusivamente para RECEPCIONISTA e GERENTE.
    """
    repository = ServicosRepository(db)
    handler = EditarServicoHandler(repository)
    return await handler.executar(id, payload)
