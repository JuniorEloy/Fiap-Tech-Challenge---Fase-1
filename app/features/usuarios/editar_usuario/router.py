from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role

from app.features.usuarios.editar_usuario.handler import EditarUsuarioHandler
from app.features.usuarios.editar_usuario.schemas import (
    EditarUsuarioRequest,
    UsuarioEditadoResponse,
)

router = APIRouter(prefix="/usuarios", tags=["Gestão de Usuários"])


@router.put(
    "/{id}",
    response_model=UsuarioEditadoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requer_roles([Role.GERENTE]))],
)
async def editar_operador(
    id: UUID,
    payload: EditarUsuarioRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Atualiza os dados cadastrais, cargo (role) ou status de um operador da oficina.
    Acesso restrito exclusivamente para o GERENTE.
    """
    handler = EditarUsuarioHandler(db)
    return await handler.executar(id, payload)
