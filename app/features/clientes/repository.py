from uuid import UUID
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.clientes.models import Cliente
from app.features.veiculos.models import Veiculo
from app.features.ordens_servico.models import OrdemServico


class ClienteRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def listar(self) -> Sequence[Cliente]:
        """Retorna todos os clientes cadastrados."""
        result = await self.db.execute(select(Cliente))
        return result.scalars().all()

    async def buscar_por_cpf_cnpj(self, cpf_cnpj: str) -> Cliente | None:
        """Busca um cliente pelo CPF ou CNPJ higienizado."""
        result = await self.db.execute(
            select(Cliente).where(Cliente.cpf_cnpj == cpf_cnpj)
        )
        return result.scalar_one_or_none()

    async def buscar_por_id(self, cliente_id: UUID) -> Cliente | None:
        """Busca um cliente pelo seu ID único (UUID)."""
        result = await self.db.execute(select(Cliente).where(Cliente.id == cliente_id))
        return result.scalar_one_or_none()

    async def possui_veiculos_ou_ordens(self, cliente_id: UUID) -> bool:
        """
        Verifica se o cliente possui veiculos cadastrados ou Ordens de Servico
        associadas para impedir a quebra de integridade referencial.
        """
        # Verifica veiculos
        stmt_vei = select(Veiculo).where(Veiculo.cliente_id == cliente_id)
        res_vei = await self.db.execute(stmt_vei)
        if res_vei.scalars().first() is not None:
            return True

        # Verifica ordens de servico
        stmt_os = select(OrdemServico).where(OrdemServico.cliente_id == cliente_id)
        res_os = await self.db.execute(stmt_os)
        if res_os.scalars().first() is not None:
            return True

        return False

    async def excluir(self, cliente: Cliente) -> None:
        await self.db.delete(cliente)

    async def salvar(self, cliente: Cliente) -> Cliente:
        """
        Persiste (insere ou atualiza) um cliente no banco de dados.
        Encapsula a lógica de infraestrutura e transação.
        """
        self.db.add(cliente)
        await self.db.commit()
        await self.db.refresh(cliente)
        return cliente
