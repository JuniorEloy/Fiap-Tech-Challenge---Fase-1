from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role

from app.features.estoque.repository import EstoqueRepository
from app.features.estoque.baixar_estoque.handler import BaixarEstoqueHandler
from app.features.estoque.baixar_estoque.schemas import (
    BaixarEstoqueRequest,
    BaixaEstoqueResponse,
)

router = APIRouter(prefix="/estoque", tags=["Gestão de Estoque"])


@router.post(
    "/baixas",
    response_model=BaixaEstoqueResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requer_roles([Role.MECANICO, Role.GERENTE]))],
)
async def baixar_saldo_estoque(
    payload: BaixarEstoqueRequest, db: AsyncSession = Depends(get_db)
):
    """
    Deduz saldo físico de peças e insumos do estoque da oficina.
    Endpoint otimizado com bloqueio pessimista de concorrência.
    Acesso permitido para MECÂNICOS e GERENTES.
    """
    repository = EstoqueRepository(db)
    handler = BaixarEstoqueHandler(repository)
    return await handler.executar(payload)
