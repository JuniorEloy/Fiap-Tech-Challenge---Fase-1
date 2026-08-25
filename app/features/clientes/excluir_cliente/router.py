from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role
from app.features.clientes.repository import ClienteRepository
from app.features.clientes.excluir_cliente.handler import ExcluirClienteHandler
from app.features.usuarios.models import Usuario

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_cliente(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(requer_roles([Role.GERENTE]))],
):
    """
    Exclui um cliente cadastrado do sistema de forma fisica.
    Operacao restrita ao papel de GERENTE. Bloqueia a exclusao caso existam vinculos ativos.
    """
    repository = ClienteRepository(db)
    handler = ExcluirClienteHandler(repository)
    await handler.executar(id)
