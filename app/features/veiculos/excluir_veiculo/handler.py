from uuid import UUID
from fastapi import HTTPException, status
from app.features.veiculos.repository import VeiculoRepository


class ExcluirVeiculoHandler:
    def __init__(self, repository: VeiculoRepository):
        self.repository = repository

    async def executar(self, id: UUID) -> None:
        veiculo = await self.repository.buscar_por_id(id)
        if not veiculo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Veiculo nao encontrado no sistema.",
            )

        if await self.repository.possui_ordens_servico(id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nao e possivel excluir este veiculo pois ele possui ordens de servico vinculadas.",
            )

        await self.repository.excluir(veiculo)
        await self.repository.db.commit()
