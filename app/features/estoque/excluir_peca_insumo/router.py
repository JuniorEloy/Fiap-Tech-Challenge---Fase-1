from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role
from app.features.estoque.repository import EstoqueRepository
from app.features.estoque.excluir_peca_insumo.handler import ExcluirPecaHandler
from app.features.usuarios.models import Usuario

router = APIRouter(prefix="/estoque", tags=["Estoque"])


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_peca(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(requer_roles([Role.GERENTE]))],
):
    """
    Remove uma peca ou insumo do catalogo de estoque.
    Operacao restrita ao papel de GERENTE. Protege o historico financeiro impedindo a remocao de pecas ja faturadas.
    """
    repository = EstoqueRepository(db)
    handler = ExcluirPecaHandler(repository)
    await handler.executar(id)
