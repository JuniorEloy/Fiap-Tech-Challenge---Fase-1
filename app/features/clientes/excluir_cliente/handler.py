from uuid import UUID
from fastapi import HTTPException, status
from app.features.clientes.repository import ClienteRepository
from app.features.clientes.excluir_cliente.schemas import ExcluirClienteResponse


class ExcluirClienteHandler:
    def __init__(self, repository: ClienteRepository):
        self.repository = repository

    async def executar(self, id: UUID) -> ExcluirClienteResponse:
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

        # Captura os dados antes de apagar fisicamente do banco
        cliente_id = cliente.id
        nome_cliente = cliente.nome

        await self.repository.excluir(cliente)
        await self.repository.db.commit()

        return ExcluirClienteResponse(
            cliente_id=cliente_id,
            nome=nome_cliente,
            mensagem=f"O cliente '{nome_cliente}' foi removido com sucesso do sistema.",
        )
