from uuid import UUID
from fastapi import HTTPException, status
from app.features.clientes.repository import ClienteRepository


class ExcluirClienteHandler:
    def __init__(self, repository: ClienteRepository):
        self.repository = repository

    async def executar(self, id: UUID) -> None:
        cliente = await self.repository.buscar_por_id(id)
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente nao encontrado no sistema.",
            )

        if await self.repository.possui_veiculos_ou_ordens(id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nao e possivel excluir este cliente pois ele possui veiculos ou ordens de servico vinculadas.",
            )

        await self.repository.excluir(cliente)
        await self.repository.db.commit()
