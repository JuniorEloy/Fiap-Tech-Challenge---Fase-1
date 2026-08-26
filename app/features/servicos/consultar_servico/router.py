from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role

from app.features.servicos.repository import ServicosRepository
from app.features.servicos.consultar_servico.handler import ConsultarServicoHandler
from app.features.servicos.schemas import ServicoResponse

router = APIRouter(prefix="/servicos", tags=["Gestão de Serviços"])


@router.get(
    "/{id}",
    response_model=ServicoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(requer_roles([Role.RECEPCIONISTA, Role.MECANICO, Role.GERENTE]))
    ],
)
async def consultar_servico_por_id(
    id: UUID, db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Recupera os detalhes cadastrais e preços de um serviço base por ID.
    Acesso permitido para RECEPCIONISTA, MECÂNICO e GERENTE.
    """
    repository = ServicosRepository(db)
    handler = ConsultarServicoHandler(repository)
    return await handler.executar(id)
