from uuid import UUID
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.clientes.models import Cliente


class ClienteRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def listar(self) -> Sequence[Cliente]:
        result = await self.db.execute(select(Cliente))
        return result.scalars().all()

    async def buscar_por_cpf_cnpj(self, cpf_cnpj: str) -> Cliente | None:
        result = await self.db.execute(
            select(Cliente).where(Cliente.cpf_cnpj == cpf_cnpj)
        )
        return result.scalar_one_or_none()

    async def buscar_por_id(self, cliente_id: UUID) -> Cliente | None:
        result = await self.db.execute(select(Cliente).where(Cliente.id == cliente_id))
        return result.scalar_one_or_none()
