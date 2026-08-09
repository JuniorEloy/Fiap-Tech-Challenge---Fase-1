from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role

from app.features.veiculos.repository import VeiculoRepository
from app.features.clientes.repository import ClienteRepository
from app.features.veiculos.editar_veiculo.handler import EditarVeiculoHandler
from app.features.veiculos.editar_veiculo.schemas import (
    EditarVeiculoRequest,
    VeiculoEditadoResponse,
)

router = APIRouter(prefix="/veiculos", tags=["Veículos"])


@router.put(
    "/{id}",
    response_model=VeiculoEditadoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requer_roles([Role.RECEPCIONISTA, Role.GERENTE]))],
)
async def editar_veiculo(
    id: UUID,
    payload: EditarVeiculoRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Edita os dados ou transfere a propriedade de um veículo cadastrado.
    Acesso restrito para RECEPCIONISTA ou GERENTE.
    """
    veiculo_repo = VeiculoRepository(db)
    cliente_repo = ClienteRepository(db)
    handler = EditarVeiculoHandler(veiculo_repo, cliente_repo)
    return await handler.executar(id, payload)
