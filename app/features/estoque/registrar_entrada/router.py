from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role

from app.features.estoque.repository import EstoqueRepository
from app.features.estoque.registrar_entrada.handler import RegistrarEntradaHandler
from app.features.estoque.registrar_entrada.schemas import RegistrarEntradaRequest, RegistroEntradaResponse

router = APIRouter(prefix="/estoque", tags=["Gestão de Estoque"])


@router.post(
    "/entradas",
    response_model=RegistroEntradaResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requer_roles([Role.ESTOQUISTA, Role.GERENTE]))]
)
async def registrar_entrada_estoque(
    payload: RegistrarEntradaRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Registra a entrada física de novas unidades de uma peça no estoque.
    Endpoint protegido com bloqueio pessimista de concorrência.
    Acesso permitido exclusivamente para ESTOQUISTAS e GERENTES.
    """
    repository = EstoqueRepository(db)
    handler = RegistrarEntradaHandler(repository)
    return await handler.executar(payload)