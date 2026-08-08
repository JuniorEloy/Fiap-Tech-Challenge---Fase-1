from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import obter_usuario_atual
from app.shared.security.rbac import requer_roles
from app.shared.security.schemas import UsuarioToken
from app.shared.security.roles import Role

from app.features.clientes.cadastrar_cliente.schemas import (
    CadastrarClienteRequest,
    ClienteResponse,
)
from app.features.clientes.cadastrar_cliente.handler import CadastrarClienteHandler
from app.features.clientes.repository import ClienteRepository

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.post(
    "",
    response_model=ClienteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requer_roles([Role.RECEPCIONISTA, Role.GERENTE]))],
)
async def cadastrar_cliente(
    payload: CadastrarClienteRequest,
    db: AsyncSession = Depends(get_db),
    usuario_logado: UsuarioToken = Depends(obter_usuario_atual),
):
    """
    Cadastra um novo cliente no sistema (Pessoa Física ou Jurídica).
    Acesso restrito para RECEPCIONISTA ou GERENTE.
    """
    repository = ClienteRepository(db)
    handler = CadastrarClienteHandler(repository)
    return await handler.executar(payload)
