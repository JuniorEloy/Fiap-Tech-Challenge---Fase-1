from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role
from app.features.veiculos.repository import VeiculoRepository
from app.features.veiculos.excluir_veiculo.handler import ExcluirVeiculoHandler
from app.features.veiculos.excluir_veiculo.schemas import ExcluirVeiculoResponse
from app.features.usuarios.models import Usuario

router = APIRouter(prefix="/veiculos", tags=["Veiculos"])


@router.delete(
    "/{id}", response_model=ExcluirVeiculoResponse, status_code=status.HTTP_200_OK
)
async def excluir_veiculo(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(requer_roles([Role.GERENTE]))],
):
    repository = VeiculoRepository(db)
    handler = ExcluirVeiculoHandler(repository)
    return await handler.executar(id)
