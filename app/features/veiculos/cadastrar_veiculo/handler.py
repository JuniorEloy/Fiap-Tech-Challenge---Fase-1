from fastapi import HTTPException, status
from app.features.veiculos.models import Veiculo
from app.features.veiculos.repository import VeiculoRepository
from app.features.clientes.repository import ClienteRepository
from app.features.veiculos.cadastrar_veiculo.schemas import (
    CadastrarVeiculoRequest,
    VeiculoResponse,
)


class CadastrarVeiculoHandler:
    def __init__(
        self,
        veiculo_repository: VeiculoRepository,
        cliente_repository: ClienteRepository,
    ):
        self.veiculo_repo = veiculo_repository
        self.cliente_repo = cliente_repository

    async def executar(self, command: CadastrarVeiculoRequest) -> VeiculoResponse:
        """
        Executa o caso de uso de cadastro de veículo:
        1. Valida se o Cliente existe no sistema (Consistência de Negócio).
        2. Valida se a Placa já existe (Garante Unicidade de placa).
        3. Persiste o Veículo e retorna o payload formatado.
        """
        # 1. Garante que o cliente proprietário é válido
        cliente = await self.cliente_repo.buscar_por_id(command.cliente_id)
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente proprietário não cadastrado.",
            )

        # 2. Garante que a placa não está duplicada no banco
        veiculo_existente = await self.veiculo_repo.buscar_por_placa(command.placa)
        if veiculo_existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe um veículo cadastrado com esta placa.",
            )

        # 3. Cria a entidade de Domínio
        novo_veiculo = Veiculo(
            placa=command.placa,
            marca=command.marca,
            modelo=command.modelo,
            ano=command.ano,
            cliente_id=command.cliente_id,
        )

        # 4. Grava no banco de dados de forma transacional
        veiculo_salvo = await self.veiculo_repo.salvar(novo_veiculo)

        return VeiculoResponse.model_validate(veiculo_salvo)
