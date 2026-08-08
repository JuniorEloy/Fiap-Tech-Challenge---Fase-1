from fastapi import HTTPException, status
from app.features.estoque.models import PecaInsumo
from app.features.estoque.repository import EstoqueRepository
from app.features.estoque.cadastrar_peca_insumo.schemas import (
    CadastrarPecaRequest,
    PecaResponse,
)


class CadastrarPecaHandler:
    def __init__(self, repository: EstoqueRepository):
        self.repository = repository

    async def executar(self, command: CadastrarPecaRequest) -> PecaResponse:
        """
        Orquestra a catalogação de uma nova peça:
        1. Valida se o item já existe no catálogo (prevenção de duplicidade concorrente).
        2. Instancia a Entidade de Domínio PecaInsumo.
        3. Persiste no banco de dados e expõe o DTO estruturado.
        """
        # 1. Valida se já existe uma peça ativa com este nome
        peca_existente = await self.repository.buscar_por_nome(command.nome)
        if peca_existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe uma peça ou insumo cadastrado com este nome.",
            )

        # 2. Cria a entidade de Domínio com UUIDv7 gerado implicitamente no construtor
        nova_peca = PecaInsumo(
            nome=command.nome,
            descricao=command.descricao,
            quantidade_em_estoque=command.quantidade_inicial,
            preco_custo=command.preco_custo,
            preco_venda=command.preco_venda,
            limite_minimo=command.limite_minimo,
        )

        # 3. Salva no banco de dados
        peca_salva = await self.repository.salvar(nova_peca)

        return PecaResponse.model_validate(peca_salva)
