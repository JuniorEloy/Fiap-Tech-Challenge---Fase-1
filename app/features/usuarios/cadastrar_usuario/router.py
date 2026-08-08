from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role

from app.features.usuarios.repository import UsuarioRepository
from app.features.usuarios.cadastrar_usuario.handler import CadastrarUsuarioHandler
from app.features.usuarios.cadastrar_usuario.schemas import (
    CriarUsuarioRequest,
    UsuarioResponse,
)

router = APIRouter(prefix="/usuarios", tags=["Gestão de Usuários"])


@router.post(
    "",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(requer_roles([Role.GERENTE]))
    ],  # 👈 Protegida exclusivamente para Gerentes!
)
async def cadastrar_operador(
    body: CriarUsuarioRequest, db: AsyncSession = Depends(get_db)
):
    """
    Cadastra um novo operador no sistema administrativo da oficina.
    Acesso exclusivo para GERENTE.
    """
    repository = UsuarioRepository(db)
    handler = CadastrarUsuarioHandler(repository)
    return await handler.executar(body)
