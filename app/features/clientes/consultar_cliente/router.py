from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from ..repository import ClienteRepository
from .handler import ConsultarClienteHandler
from .schemas import ClienteResponse
from app.shared.security.rbac import requer_roles
from app.shared.security.roles import Role
from app.shared.security.dependencies import obter_usuario_atual
from app.shared.security.schemas import UsuarioToken
from app.shared.security.dependencies import validar_propriedade_ou_role

router = APIRouter(
    prefix="/clientes",
    tags=["Clientes"],
)


@router.get(
    "",
    response_model=List[ClienteResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar todos os clientes",
    dependencies=[Depends(requer_roles([Role.GERENTE]))],
)
async def listar_clientes(
    db: AsyncSession = Depends(get_db),
):
    repo = ClienteRepository(db)
    handler = ConsultarClienteHandler(repo)

    return await handler.listar_todos()


@router.get(
    "/documento/{documento}",
    response_model=ClienteResponse,
    status_code=status.HTTP_200_OK,
    summary="Buscar cliente por CPF ou CNPJ",
    dependencies=[Depends(requer_roles([Role.GERENTE, Role.RECEPCIONISTA]))],
)
async def buscar_cliente_por_documento(
    documento: str,
    db: AsyncSession = Depends(get_db),
):
    repo = ClienteRepository(db)
    handler = ConsultarClienteHandler(repo)
    return await handler.buscar_por_cpf_cnpj(documento)


@router.get(
    "/{cliente_id}",
    response_model=ClienteResponse,
    status_code=status.HTTP_200_OK,
    summary="Buscar cliente por ID (UUID)",
    dependencies=[
        Depends(requer_roles([Role.GERENTE, Role.RECEPCIONISTA, Role.CLIENTE]))
    ],
)
async def buscar_cliente_por_id(
    cliente_id: UUID,
    usuario_atual: UsuarioToken = Depends(obter_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    # 🛡️ 2. Valida IDOR ANTES de ir ao banco de dados:
    # - Se for CLIENTE e cliente_id != usuario_atual.id -> Lança 403 Forbidden imediatamente!
    # - Se for GERENTE ou RECEPCIONISTA -> Passa reto pelo roles_bypass.
    validar_propriedade_ou_role(
        resource_owner_id=cliente_id,
        usuario_atual=usuario_atual,
        roles_bypass=[Role.GERENTE, Role.RECEPCIONISTA],
    )

    # 🔍 3. Só consulta o banco se tiver permissão sobre este ID específico
    repo = ClienteRepository(db)
    handler = ConsultarClienteHandler(repo)
    return await handler.buscar_por_id(cliente_id)
