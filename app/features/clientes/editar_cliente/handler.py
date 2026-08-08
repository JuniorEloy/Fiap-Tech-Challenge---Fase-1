from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select

from app.features.clientes.repository import ClienteRepository
from app.features.clientes.models import Cliente
from app.features.clientes.editar_cliente.schemas import (
    EditarClienteRequest,
    ClienteEditadoResponse,
)
from app.features.usuarios.models import (
    Usuario,
)


class EditarClienteHandler:
    def __init__(self, repository: ClienteRepository):
        self.repository = repository

    async def executar(
        self, cliente_id: UUID, command: EditarClienteRequest
    ) -> ClienteEditadoResponse:
        """
        Orquestra a edição cadastral do cliente:
        1. Busca o cliente pelo ID.
        2. Valida duplicidade de e-mail e documento (se alterados).
        3. Atualiza os dados de negócio do Cliente.
        4. Sincroniza dados de login (nome, email) no Usuário vinculado.
        5. Persiste as modificações.
        """
        # 1. Busca o cliente
        cliente = await self.repository.buscar_por_id(cliente_id)
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado."
            )

        # 2. Valida e-mail duplicado em Clientes e Usuários
        if command.email and command.email != cliente.email:
            query_cli_email = select(Cliente).where(
                Cliente.email == command.email, Cliente.id != cliente_id
            )
            res_cli_email = await self.repository.db.execute(query_cli_email)
            if res_cli_email.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="O e-mail informado já está em uso por outro cliente.",
                )

            query_usr_email = select(Usuario).where(
                Usuario.email == command.email, Usuario.id != cliente.usuario_id
            )
            res_usr_email = await self.repository.db.execute(query_usr_email)
            if res_usr_email.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="O e-mail informado já está em uso por outro usuário.",
                )

        # Valida CPF/CNPJ duplicado
        if command.cpf_cnpj and command.cpf_cnpj != cliente.cpf_cnpj:
            cliente_existente = await self.repository.buscar_por_cpf_cnpj(
                command.cpf_cnpj
            )
            if cliente_existente and cliente_existente.id != cliente_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Já existe um cliente cadastrado com o documento informado.",
                )

        # 3. Busca o Usuário associado para sincronização de login
        query_usuario = select(Usuario).where(Usuario.id == cliente.usuario_id)
        res_usuario = await self.repository.db.execute(query_usuario)
        usuario = res_usuario.scalar_one_or_none()

        # 4. Atualização parcial e sincronização
        if command.nome is not None:
            cliente.nome = command.nome
            if usuario:
                usuario.nome = command.nome

        if command.email is not None:
            cliente.email = command.email
            if usuario:
                usuario.email = command.email

        if command.telefone is not None:
            cliente.telefone = command.telefone

        if command.cpf_cnpj is not None:
            cliente.cpf_cnpj = command.cpf_cnpj

        if command.tipo_pessoa is not None:
            cliente.tipo_pessoa = command.tipo_pessoa

        # 5. Salva delegando as transações ao repositório unificado
        cliente_salvo = await self.repository.salvar(cliente)

        return ClienteEditadoResponse.model_validate(cliente_salvo)
