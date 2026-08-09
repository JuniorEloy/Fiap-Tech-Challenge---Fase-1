from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role

from app.features.usuarios.consultar_usuario.handler import ConsultarUsuarioHandler
from app.features.usuarios.consultar_usuario.schemas import ConsultarUsuarioResponse

router = APIRouter(prefix="/usuarios", tags=["Gestão de Usuários"])


@router.get(
    "/{id}",
    response_model=ConsultarUsuarioResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requer_roles([Role.GERENTE]))],
)
async def consultar_operador(id: UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Retorna os dados cadastrais detalhados de um operador administrativo da oficina.
    Acesso restrito exclusivamente para o GERENTE.
    """
    handler = ConsultarUsuarioHandler(db)
    return await handler.executar(id)
