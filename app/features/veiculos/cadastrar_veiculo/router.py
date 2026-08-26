from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role

from app.features.veiculos.repository import VeiculoRepository
from app.features.clientes.repository import ClienteRepository
from app.features.veiculos.cadastrar_veiculo.handler import CadastrarVeiculoHandler
from app.features.veiculos.cadastrar_veiculo.schemas import (
    CadastrarVeiculoRequest,
    VeiculoResponse,
)

router = APIRouter(prefix="/veiculos", tags=["Veículos"])


@router.post(
    "",
    response_model=VeiculoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requer_roles([Role.RECEPCIONISTA, Role.GERENTE]))],
)
async def cadastrar_veiculo(
    payload: CadastrarVeiculoRequest, db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Registra um novo veículo associado a um cliente.
    Acesso autorizado apenas para RECEPCIONISTA ou GERENTE.
    """
    veiculo_repo = VeiculoRepository(db)
    cliente_repo = ClienteRepository(db)
    handler = CadastrarVeiculoHandler(veiculo_repo, cliente_repo)
    return await handler.executar(payload)
