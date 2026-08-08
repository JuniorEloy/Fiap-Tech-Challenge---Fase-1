from uuid import UUID
from fastapi import HTTPException, status
from app.features.veiculos.repository import VeiculoRepository
from app.features.clientes.repository import ClienteRepository
from app.features.veiculos.editar_veiculo.schemas import (
    EditarVeiculoRequest,
    VeiculoEditadoResponse,
)


class EditarVeiculoHandler:
    def __init__(
        self,
        veiculo_repository: VeiculoRepository,
        cliente_repository: ClienteRepository,
    ):
        self.veiculo_repo = veiculo_repository
        self.cliente_repo = cliente_repository

    async def executar(
        self, veiculo_id: UUID, command: EditarVeiculoRequest
    ) -> VeiculoEditadoResponse:
        """
        Executa as regras de domínio para a edição de veículos:
        1. Valida a existência do veículo.
        2. Se houver troca de proprietário (cliente_id), valida se o novo cliente existe.
        3. Se houver correção de placa, garante a integridade de unicidade.
        4. Salva e retorna o DTO de projeção formatado.
        """
        # 1. Verifica existência do veículo
        veiculo = await self.veiculo_repo.buscar_por_id(veiculo_id)
        if not veiculo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado."
            )

        # 2. Se houver alteração de proprietário, valida o novo ID
        if command.cliente_id and command.cliente_id != veiculo.cliente_id:
            cliente_existe = await self.cliente_repo.buscar_por_id(command.cliente_id)
            if not cliente_existe:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cliente proprietário não cadastrado.",
                )

        # 3. Se houver correção de placa, valida duplicidade no banco
        if command.placa and command.placa != veiculo.placa:
            veiculo_existente = await self.veiculo_repo.buscar_por_placa(command.placa)
            if veiculo_existente and veiculo_existente.id != veiculo_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Já existe um veículo cadastrado com esta placa.",
                )

        # 4. Aplica alterações parciais
        if command.placa is not None:
            veiculo.placa = command.placa
        if command.marca is not None:
            veiculo.marca = command.marca
        if command.modelo is not None:
            veiculo.modelo = command.modelo
        if command.ano is not None:
            veiculo.ano = command.ano
        if command.cliente_id is not None:
            veiculo.cliente_id = command.cliente_id

        # 5. Persiste as modificações
        veiculo_salvo = await self.veiculo_repo.salvar(veiculo)
        return VeiculoEditadoResponse.model_validate(veiculo_salvo)
