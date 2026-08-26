from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role
from app.features.estoque.repository import EstoqueRepository
from app.features.estoque.excluir_peca_insumo.handler import ExcluirPecaHandler
from app.features.estoque.excluir_peca_insumo.schemas import ExcluirPecaResponse
from app.features.usuarios.models import Usuario

router = APIRouter(prefix="/estoque", tags=["Estoque"])


@router.delete(
    "/{id}", response_model=ExcluirPecaResponse, status_code=status.HTTP_200_OK
)
async def excluir_peca(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(requer_roles([Role.GERENTE]))],
):
    repository = EstoqueRepository(db)
    handler = ExcluirPecaHandler(repository)
    return await handler.executar(id)
