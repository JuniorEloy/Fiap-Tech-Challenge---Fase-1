from uuid import UUID
from fastapi import HTTPException, status
from app.features.servicos.repository import ServicosRepository
from app.features.servicos.editar_servico.schemas import EditarServicoRequest
from app.features.servicos.cadastrar_servico.schemas import ServicoResponse


class EditarServicoHandler:
    def __init__(self, repository: ServicosRepository):
        self.repository = repository

    async def executar(
        self, servico_id: UUID, command: EditarServicoRequest
    ) -> ServicoResponse:
        """
        Executa as validações operacionais e persiste as alterações:
        1. Carrega o serviço base correspondente pelo ID.
        2. Se houver alteração de nome, garante que este nome não conflite com outro serviço catalogado.
        3. Realiza a atribuição seletiva dos campos.
        4. Salva e commita as alterações no banco de dados.
        """
        # 1. Carrega o registro do banco
        servico = await self.repository.buscar_por_id(servico_id)
        if not servico:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Serviço não encontrado no catálogo da oficina.",
            )

        # 2. Se o nome mudou, garante unicidade cadastral no banco de dados
        if command.nome is not None and command.nome != servico.nome:
            servico_conflitante = await self.repository.buscar_por_nome(command.nome)
            if servico_conflitante:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Já existe outro serviço cadastrado com este nome no catálogo.",
                )

        # 3. Aplica atualizações seletivas
        if command.nome is not None:
            servico.nome = command.nome
        if command.descricao is not None:
            servico.descricao = command.descricao
        if command.preco_mao_de_obra is not None:
            servico.preco_mao_de_obra = command.preco_mao_de_obra
        if command.duracao_estimada_minutos is not None:
            servico.duracao_estimada_minutos = command.duracao_estimada_minutos
        if command.ativo is not None:
            servico.ativo = command.ativo
        if command.permite_servico_expresso is not None:
            servico.permite_servico_expresso = command.permite_servico_expresso

        # 4. Grava transacionalmente as alterações
        servico_atualizado = await self.repository.salvar(servico)

        return ServicoResponse.model_validate(servico_atualizado)
