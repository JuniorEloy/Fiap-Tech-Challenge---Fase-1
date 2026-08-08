# app/features/estoque/repository.py
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.estoque.models import PecaInsumo


class EstoqueRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def buscar_por_id(self, peca_id: UUID) -> PecaInsumo | None:
        """Busca uma peça/insumo pelo ID."""
        result = await self.db.execute(
            select(PecaInsumo).where(PecaInsumo.id == peca_id)
        )
        return result.scalar_one_or_none()

    async def buscar_por_nome(self, nome: str) -> PecaInsumo | None:
        """
        Busca uma peça pelo nome exato para validação de unicidade cadastral.
        Isso ajuda a prevenir duplicidades concorrentes na base de dados.
        """
        result = await self.db.execute(
            select(PecaInsumo).where(PecaInsumo.nome == nome)
        )
        return result.scalars().first()

    async def salvar(self, peca: PecaInsumo) -> PecaInsumo:
        """Persiste ou atualiza a entidade de estoque de forma transacional."""
        self.db.add(peca)
        await self.db.commit()
        await self.db.refresh(peca)
        return peca
