from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.estoque.models import PecaInsumo


class EstoqueRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def buscar_por_id(self, peca_id: UUID) -> PecaInsumo | None:
        """Busca uma peça/insumo pelo ID (leitura simples)."""
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
        return result.scalars().first()  # Retorna o primeiro registro ou None

    async def buscar_por_id_com_bloqueio(self, peca_id: UUID) -> PecaInsumo | None:
        """
        🛡️ Busca uma peça aplicando FOR UPDATE no banco de dados.
        Bloqueia a linha contra leituras concorrentes para escrita até o fim da transação.
        Previne condições de corrida de saldo de estoque.
        """
        query = select(PecaInsumo).where(PecaInsumo.id == peca_id).with_for_update()
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def salvar(self, peca: PecaInsumo) -> PecaInsumo:
        """Persiste ou atualiza a entidade de estoque."""
        self.db.add(peca)
        await self.db.commit()
        await self.db.refresh(peca)
        return peca
