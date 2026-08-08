from fastapi import HTTPException, status
from app.features.veiculos.repository import VeiculoRepository
from app.features.veiculos.consultar_veiculo.schemas import ConsultarVeiculoResponse
from app.shared.domain.value_objects.placa import Placa


class ConsultarVeiculoHandler:
    def __init__(self, repository: VeiculoRepository):
        self.repository = repository

    async def executar(self, placa_str: str) -> ConsultarVeiculoResponse:
        """
        Executa a busca estruturada pela placa do carro.
        Valida a placa usando o Value Object antes de consultar o banco.
        """
        try:
            placa_vo = Placa(placa_str)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            )

        veiculo = await self.repository.buscar_por_placa(placa_vo.valor)
        if not veiculo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado."
            )

        return ConsultarVeiculoResponse.model_validate(veiculo)
