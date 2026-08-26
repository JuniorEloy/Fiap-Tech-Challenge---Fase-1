from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role
from app.features.clientes.repository import ClienteRepository
from app.features.clientes.excluir_cliente.handler import ExcluirClienteHandler
from app.features.clientes.excluir_cliente.schemas import ExcluirClienteResponse
from app.features.usuarios.models import Usuario

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.delete(
    "/{id}", response_model=ExcluirClienteResponse, status_code=status.HTTP_200_OK
)
async def excluir_cliente(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(requer_roles([Role.GERENTE]))],
):
    repository = ClienteRepository(db)
    handler = ExcluirClienteHandler(repository)
    return await handler.executar(id)
