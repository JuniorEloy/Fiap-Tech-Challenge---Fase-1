from uuid import UUID
from fastapi import HTTPException, status
from app.features.servicos.repository import ServicosRepository
from app.features.servicos.excluir_servico.schemas import DesativarServicoResponse


class ExcluirServicoHandler:
    def __init__(self, repository: ServicosRepository):
        self.repository = repository

    async def executar(self, servico_id: UUID) -> DesativarServicoResponse:
        servico = await self.repository.buscar_por_id(servico_id)
        if not servico:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Serviço não encontrado no catálogo da oficina.",
            )

        # Soft Delete: Inativa o serviço
        servico.ativo = False
        await self.repository.salvar(servico)

        return DesativarServicoResponse(
            servico_id=servico.id,
            nome=servico.nome,
            ativo=False,
            mensagem=f"O serviço '{servico.nome}' foi desativado com sucesso do catálogo da oficina.",
        )
