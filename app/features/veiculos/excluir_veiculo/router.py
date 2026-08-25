from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role
from app.features.veiculos.repository import VeiculoRepository
from app.features.veiculos.excluir_veiculo.handler import ExcluirVeiculoHandler

router = APIRouter(prefix="/veiculos", tags=["Veiculos"])


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_veiculo(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(requer_roles([Role.GERENTE]))],
):
    """
    Exclui um veiculo cadastrado do sistema.
    Operacao restrita ao papel de GERENTE. Impede a remocao se houver historico de OS.
    """
    repository = VeiculoRepository(db)
    handler = ExcluirVeiculoHandler(repository)
    await handler.executar(id)
