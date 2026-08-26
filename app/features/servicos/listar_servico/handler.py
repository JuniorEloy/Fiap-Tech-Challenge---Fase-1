from typing import Optional, List
from app.features.servicos.repository import ServicosRepository
from app.features.servicos.schemas import ServicoResponse


class ListarServicosHandler:
    def __init__(self, repository: ServicosRepository):
        self.repository = repository

    async def executar(
        self,
        busca: Optional[str] = None,
        ativo: Optional[bool] = None,
        page: int = 1,
        limit: int = 100,
    ) -> List[ServicoResponse]:
        """
        Retorna a lista de serviços do catálogo filtrados e formatados como DTO.
        """
        # Previne paginação com valores inválidos
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 100

        offset = (page - 1) * limit

        servicos = await self.repository.listar_filtrado(
            busca=busca, ativo=ativo, limit=limit, offset=offset
        )

        return [ServicoResponse.model_validate(s) for s in servicos]
