from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.servicos.models import ServicoBase


class ServicosRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def buscar_por_id(self, servico_id: UUID) -> ServicoBase | None:
        """Busca um serviço cadastrado pelo ID."""
        result = await self.db.execute(
            select(ServicoBase).where(ServicoBase.id == servico_id)
        )
        return result.scalar_one_or_none()

    async def buscar_por_nome(self, nome: str) -> ServicoBase | None:
        """
        Busca um serviço pelo nome exato para validação de unicidade cadastral.
        Previne a duplicação no catálogo da oficina.
        """
        result = await self.db.execute(
            select(ServicoBase).where(ServicoBase.nome == nome)
        )
        return result.scalars().first()

    async def salvar(self, servico: ServicoBase) -> ServicoBase:
        """Persiste ou atualiza a entidade de serviços de forma transacional."""
        self.db.add(servico)
        await self.db.commit()
        await self.db.refresh(servico)
        return servico
