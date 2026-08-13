from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import requer_roles
from app.shared.security.roles import Role

from app.features.relatorios.tempo_medio.query_service import (
    RelatorioTempoMedioQueryService,
)
from app.features.relatorios.tempo_medio.schemas import RelatorioTempoMedioResponse

router = APIRouter(prefix="/relatorios", tags=["Relatórios Gerenciais"])


@router.get(
    "/tempo_medio",
    response_model=RelatorioTempoMedioResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(requer_roles([Role.GERENTE]))],
)
async def obter_relatorio_tempo_medio_pátio(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Retorna o relatório executivo de tempos operacionais e eficiência de pátio da oficina.
    Calcula dinamicamente leadtimes, inércia de resposta de clientes, e tempos médios de permanência por etapa.
    Endpoint restrito exclusivamente ao papel de GERENTE.
    """
    service = RelatorioTempoMedioQueryService(db)
    return await service.obter_relatorio_tempos()
