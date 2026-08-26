from fastapi import HTTPException, status
from app.features.servicos.models import ServicoBase
from app.features.servicos.repository import ServicosRepository
from app.features.servicos.cadastrar_servico.schemas import (
    CadastrarServicoRequest
)
from app.features.servicos.schemas import ServicoResponse


class CadastrarServicoHandler:
    def __init__(self, repository: ServicosRepository):
        self.repository = repository

    async def executar(self, command: CadastrarServicoRequest) -> ServicoResponse:
        """
        Orquestra o cadastro de um novo serviço:
        1. Valida se o item já existe no catálogo pelo nome (prevenção de duplicidade concorrente).
        2. Instancia a Entidade de Domínio ServicoBase.
        3. Persiste no banco de dados e expõe o DTO estruturado.
        """
        # 1. Valida se já existe um serviço ativo com este nome
        servico_existente = await self.repository.buscar_por_nome(command.nome)
        if servico_existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe um serviço cadastrado com este nome.",
            )

        # 2. Cria a entidade de Domínio com UUIDv7 gerado implicitamente no construtor
        novo_servico = ServicoBase(
            nome=command.nome,
            descricao=command.descricao,
            preco_mao_de_obra=command.preco_mao_de_obra,
            duracao_estimada_minutos=command.duracao_estimada_minutos,
            permite_servico_expresso=command.permite_servico_expresso,
            ativo=True,
        )

        # 3. Salva no banco de dados de forma transacional
        servico_salvo = await self.repository.salvar(novo_servico)

        return ServicoResponse.model_validate(servico_salvo)
