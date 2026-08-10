from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role

from app.features.estoque.relatorio_estoque_baixo.query_service import (
    RelatorioEstoqueBaixoQueryService,
)
from app.features.estoque.relatorio_estoque_baixo.schemas import (
    RelatorioEstoqueBaixoResponse,
)

router = APIRouter(prefix="/estoque/relatorios", tags=["Relatórios de Estoque"])


@router.get(
    "/baixo",
    response_model=RelatorioEstoqueBaixoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requer_roles([Role.ESTOQUISTA, Role.GERENTE]))],
)
async def obter_relatorio_estoque_baixo(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Retorna a lista analítica de peças e insumos que violaram o limite de segurança mínimo.
    Calcula dinamicamente a quantidade de reposição necessária e o aporte financeiro estimado.
    Acesso restrito para ESTOQUISTA ou GERENTE.
    """
    query_service = RelatorioEstoqueBaixoQueryService(db)
    return await query_service.obter_relatorio_critico()
