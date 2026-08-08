from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role

from app.features.relatorios.cliente_veiculo.query_service import DashboardQueryService
from app.features.relatorios.cliente_veiculo.schemas import DashboardGeralResponse

router = APIRouter(prefix="/relatorio", tags=["Relatórios & Métricas"])


@router.get(
    "/cliente-veiculo",
    response_model=DashboardGeralResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requer_roles([Role.GERENTE]))],
)
async def obter_dashboard_geral(db: AsyncSession = Depends(get_db)):
    """
    Retorna o relatório executivo completo de Veículos e Clientes cadastrados.
    Endpoint restrito de controle e análise operacional.
    Acesso permitido apenas para GERENTE.
    """
    query_service = DashboardQueryService(db)
    return await query_service.obter_dados_gerais()
