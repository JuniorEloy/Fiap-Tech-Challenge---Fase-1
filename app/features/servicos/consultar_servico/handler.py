from uuid import UUID
from fastapi import HTTPException, status
from app.features.servicos.repository import ServicosRepository
from app.features.servicos.schemas import ServicoResponse


class ConsultarServicoHandler:
    def __init__(self, repository: ServicosRepository):
        self.repository = repository

    async def executar(self, servico_id: UUID) -> ServicoResponse:
        """
        Orquestra a busca de um serviço no catálogo pelo ID:
        1. Consulta o repositório pelo UUID fornecido.
        2. Lança 404 caso o serviço não seja encontrado.
        3. Retorna o DTO correspondente.
        """
        servico = await self.repository.buscar_por_id(servico_id)
        if not servico:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Serviço não encontrado no catálogo da oficina.",
            )

        return ServicoResponse.model_validate(servico)
