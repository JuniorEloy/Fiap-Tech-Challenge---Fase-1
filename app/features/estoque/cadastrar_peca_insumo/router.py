from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role

from app.features.estoque.repository import EstoqueRepository
from app.features.estoque.cadastrar_peca_insumo.handler import CadastrarPecaHandler
from app.features.estoque.cadastrar_peca_insumo.schemas import (
    CadastrarPecaRequest,
    PecaResponse,
)

router = APIRouter(prefix="/estoque", tags=["Gestão de Estoque"])


@router.post(
    "",
    response_model=PecaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requer_roles([Role.ESTOQUISTA, Role.GERENTE]))],
)
async def cadastrar_peca_insumo(
    payload: CadastrarPecaRequest, db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Cadastra uma nova peça ou insumo de manutenção no catálogo da oficina.
    Acesso autorizado apenas para ESTOQUISTA ou GERENTE.
    """
    repository = EstoqueRepository(db)
    handler = CadastrarPecaHandler(repository)
    return await handler.executar(payload)
