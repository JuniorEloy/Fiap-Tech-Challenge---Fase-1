from uuid import UUID
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.veiculos.models import Veiculo


class VeiculoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def buscar_por_id(self, veiculo_id: UUID) -> Veiculo | None:
        result = await self.db.execute(select(Veiculo).where(Veiculo.id == veiculo_id))
        return result.scalar_one_or_none()

    async def buscar_por_placa(self, placa: str) -> Veiculo | None:
        result = await self.db.execute(select(Veiculo).where(Veiculo.placa == placa))
        return result.scalar_one_or_none()

    async def listar_por_cliente(self, cliente_id: UUID) -> Sequence[Veiculo]:
        result = await self.db.execute(
            select(Veiculo).where(Veiculo.cliente_id == cliente_id)
        )
        return result.scalars().all()

    async def salvar(self, veiculo: Veiculo) -> Veiculo:
        self.db.add(veiculo)
        await self.db.commit()
        await self.db.refresh(veiculo)
        return veiculo
