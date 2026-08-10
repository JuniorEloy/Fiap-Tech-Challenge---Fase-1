from uuid import UUID
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.servicos.models import ServicoBase
from typing import Optional, List


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

    async def listar_filtrado(
        self,
        busca: Optional[str] = None,
        ativo: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ServicoBase]:
        """
        Lista serviços catalogados aplicando filtros opcionais e paginação leve.
        """
        query = select(ServicoBase)

        # Filtro de busca textual (nome ou descrição)
        if busca:
            busca_wildcard = f"%{busca}%"
            query = query.where(
                or_(
                    ServicoBase.nome.ilike(busca_wildcard),
                    ServicoBase.descricao.ilike(busca_wildcard),
                )
            )

        # Filtro de status ativo
        if ativo is not None:
            query = query.where(ServicoBase.ativo == ativo)

        # Aplicação de paginação e ordenação alfabética
        query = query.order_by(ServicoBase.nome).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())
