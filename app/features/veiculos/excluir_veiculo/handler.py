from uuid import UUID
from fastapi import HTTPException, status
from app.features.veiculos.repository import VeiculoRepository
from app.features.veiculos.excluir_veiculo.schemas import ExcluirVeiculoResponse


class ExcluirVeiculoHandler:
    def __init__(self, repository: VeiculoRepository):
        self.repository = repository

    async def executar(self, id: UUID) -> ExcluirVeiculoResponse:
        veiculo = await self.repository.buscar_por_id(id)
        if not veiculo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Veiculo nao encontrado."
            )

        if await self.repository.possui_ordens_servico(id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nao e possivel excluir este veiculo pois ele possui ordens de servico vinculadas.",
            )

        veiculo_id = veiculo.id
        placa_veiculo = veiculo.placa

        await self.repository.excluir(veiculo)
        await self.repository.db.commit()

        return ExcluirVeiculoResponse(
            veiculo_id=veiculo_id,
            placa=placa_veiculo,
            mensagem=f"O veiculo com placa '{placa_veiculo}' foi removido com sucesso do sistema.",
        )
