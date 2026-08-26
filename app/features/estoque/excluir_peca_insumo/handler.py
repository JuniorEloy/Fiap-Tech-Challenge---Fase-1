from uuid import UUID
from fastapi import HTTPException, status
from app.features.estoque.repository import EstoqueRepository
from app.features.estoque.excluir_peca_insumo.schemas import ExcluirPecaResponse


class ExcluirPecaHandler:
    def __init__(self, repository: EstoqueRepository):
        self.repository = repository

    async def executar(self, id: UUID) -> ExcluirPecaResponse:
        peca = await self.repository.buscar_por_id(id)
        if not peca:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Peca ou insumo nao encontrado no catalogo.",
            )

        if await self.repository.esta_vinculada_a_ordens(id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nao e possivel excluir esta peca pois ela ja foi utilizada em ordens de servico historicas.",
            )

        peca_id = peca.id
        nome_peca = peca.nome

        await self.repository.excluir(peca)
        await self.repository.db.commit()

        return ExcluirPecaResponse(
            peca_id=peca_id,
            nome=nome_peca,
            mensagem=f"A peca '{nome_peca}' foi removida com sucesso do catalogo de estoque.",
        )
