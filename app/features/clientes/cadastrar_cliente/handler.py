from uuid import uuid7
from fastapi import HTTPException, status
from app.features.clientes.repository import ClienteRepository
from app.features.clientes.models import Cliente
from app.features.clientes.cadastrar_cliente.schemas import (
    CadastrarClienteRequest,
    ClienteResponse,
)
from app.features.usuarios.models import Usuario
from app.shared.security.password import gerar_hash_senha
from app.shared.security.roles import Role
from app.shared.domain.value_objects.email import Email

class CadastrarClienteHandler:
    def __init__(self, repository: ClienteRepository):
        self.repository = repository

    async def executar(self, command: CadastrarClienteRequest) -> ClienteResponse:
        # 1. Valida se o documento já existe usando o repositório
        if await self.repository.buscar_por_cpf_cnpj(command.cpf_cnpj):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe um cliente cadastrado com o documento informado.",
            )

        # 2. Criamos automaticamente a credencial (Usuario) para o Cliente
        senha_padrao_hash = gerar_hash_senha(command.cpf_cnpj)

        email_limpo = Email(command.email).valor

        novo_usuario = Usuario(
            nome=command.nome,
            email=email_limpo,
            senha=senha_padrao_hash,
            role=Role.CLIENTE,
        )

        # Adiciona o usuário na sessão do banco
        self.repository.db.add(novo_usuario)

        # 🌟 AQUI ESTÁ A CORREÇÃO: Força o insert do usuário ocorrer primeiro no Postgres!
        await self.repository.db.flush()

        # 3. Criamos a entidade Cliente apontando para o id do Usuario recém-criado
        novo_cliente = Cliente(
            id=uuid7(),
            nome=command.nome,
            email=email_limpo,
            telefone=command.telefone,
            cpf_cnpj=command.cpf_cnpj,
            tipo_pessoa=command.tipo_pessoa,
            usuario_id=novo_usuario.id,  # 🔒 Agora o ID já está garantido no banco!
        )

        # Persiste no banco de dados e realiza o commit unificado de ambos
        cliente_salvo = await self.repository.salvar(novo_cliente)

        return ClienteResponse.model_validate(cliente_salvo)
