from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role

from app.features.servicos.repository import ServicosRepository
from app.features.servicos.excluir_servico.handler import ExcluirServicoHandler
from app.features.servicos.excluir_servico.schemas import DesativarServicoResponse

router = APIRouter(prefix="/servicos", tags=["Gestão de Serviços"])


@router.delete(
    "/{id}",
    response_model=DesativarServicoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requer_roles([Role.GERENTE]))],
)
async def excluir_servico(id: UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    repository = ServicosRepository(db)
    handler = ExcluirServicoHandler(repository)
    return await handler.executar(id)
