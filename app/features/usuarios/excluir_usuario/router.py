from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role
from app.features.usuarios.repository import UsuarioRepository
from app.features.usuarios.models import Usuario
from app.features.usuarios.excluir_usuario.handler import ExcluirUsuarioHandler


router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_usuario(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(requer_roles([Role.GERENTE]))],
):
    """
    Inativa de forma logica (Soft Delete) um operador do sistema.
    Operacao restrita ao papel de GERENTE. Impede a auto-inativacao.
    """
    repository = UsuarioRepository(db)
    handler = ExcluirUsuarioHandler(repository)
    await handler.executar(id, executor_id=current_user.id)
