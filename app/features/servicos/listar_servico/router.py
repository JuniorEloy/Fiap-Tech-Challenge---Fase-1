from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role

from app.features.servicos.repository import ServicosRepository
from app.features.servicos.listar_servico.handler import ListarServicosHandler
from app.features.servicos.cadastrar_servico.schemas import ServicoResponse

router = APIRouter(prefix="/servicos", tags=["Gestão de Serviços"])


@router.get(
    "",
    response_model=List[ServicoResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(requer_roles([Role.RECEPCIONISTA, Role.MECANICO, Role.GERENTE]))
    ],
)
async def listar_servicos(
    db: Annotated[AsyncSession, Depends(get_db)],
    busca: Optional[str] = Query(
        None, description="Termo de busca para filtrar por nome ou descrição"
    ),
    ativo: Optional[bool] = Query(
        None, description="Filtrar serviços por status (ativos/inativos)"
    ),
    page: int = Query(1, ge=1, description="Número da página atual para exibição"),
    limit: int = Query(
        50, ge=1, le=100, description="Limite de itens retornados por página"
    ),
):
    """
    Lista de forma paginada e filtrada todos os serviços cadastrados no catálogo da oficina.
    Permite busca textual e filtro de ativação.
    """
    repository = ServicosRepository(db)
    handler = ListarServicosHandler(repository)
    return await handler.executar(busca=busca, ativo=ativo, page=page, limit=limit)
