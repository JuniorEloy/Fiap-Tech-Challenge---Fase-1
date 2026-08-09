from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role
from app.features.clientes.repository import ClienteRepository
from app.features.clientes.editar_cliente.handler import EditarClienteHandler
from app.features.clientes.editar_cliente.schemas import (
    EditarClienteRequest,
    ClienteEditadoResponse,
)

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.put(
    "/{id}",
    response_model=ClienteEditadoResponse,
    status_code=status.HTTP_200_OK,
)
async def editar_cliente(
    id: UUID,
    payload: EditarClienteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(
        requer_roles([Role.RECEPCIONISTA, Role.GERENTE])
    ),  # 👈 RBAC de segurança
):
    """
    Edita os dados cadastrais de um cliente existente.
    Sincroniza automaticamente nome, e-mail e status ativo com a credencial do Usuário.
    Acesso permitido para RECEPCIONISTA ou GERENTE.
    """
    repository = ClienteRepository(db)
    handler = EditarClienteHandler(repository)
    return await handler.executar(id, payload)
