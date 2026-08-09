from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from typing import Annotated
from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role

from app.features.veiculos.repository import VeiculoRepository
from app.features.veiculos.consultar_veiculo.handler import ConsultarVeiculoHandler
from app.features.veiculos.consultar_veiculo.schemas import ConsultarVeiculoResponse

router = APIRouter(prefix="/veiculos", tags=["Veículos"])


@router.get(
    "/placa/{placa}",
    response_model=ConsultarVeiculoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(requer_roles([Role.RECEPCIONISTA, Role.GERENTE, Role.MECANICO]))
    ],
)
async def consultar_veiculo_por_placa(
    placa: str, db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Busca um veículo cadastrado na oficina utilizando a placa de licença (Mercosul ou Tradicional).
    Acesso liberado para RECEPCIONISTA, GERENTE ou MECÂNICO.
    """
    repository = VeiculoRepository(db)
    handler = ConsultarVeiculoHandler(repository)
    return await handler.executar(placa)
