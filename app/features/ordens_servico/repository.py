from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.ordens_servico.models import OrdemServico, OrdemServicoStatusLog


class OrdemServicoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def buscar_por_id(self, os_id: UUID) -> OrdemServico | None:
        """Busca a OS carregando eager-loaded relacionamentos de itens."""
        result = await self.db.execute(
            select(OrdemServico).where(OrdemServico.id == os_id)
        )
        return result.scalar_one_or_none()

    async def salvar(self, os: OrdemServico) -> OrdemServico:
        """Persiste a OS na transação atual."""
        self.db.add(os)
        return os

    async def salvar_status_log(self, log: OrdemServicoStatusLog) -> None:
        """Persiste o log de auditoria de transição de status."""
        self.db.add(log)
