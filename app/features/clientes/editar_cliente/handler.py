from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select

from app.features.clientes.models import Cliente
from app.features.usuarios.models import Usuario
from app.features.clientes.repository import ClienteRepository
from app.features.clientes.editar_cliente.schemas import (
    EditarClienteRequest,
    ClienteEditadoResponse,
)
from app.shared.domain.value_objects.email import Email


class EditarClienteHandler:
    def __init__(self, repository: ClienteRepository):
        self.repository = repository

    async def executar(
        self, cliente_id: UUID, command: EditarClienteRequest
    ) -> ClienteEditadoResponse:
        """
        Orquestra a edição cadastral do cliente de forma modularizada.
        """
        cliente = await self._buscar_cliente_ou_404(cliente_id)

        email_limpo = self._higienizar_e_validar_email(command.email)

        await self._validar_conflitos_email(
            email_limpo, cliente_id, cliente.email, cliente.usuario_id
        )
        await self._validar_conflito_documento(
            command.cpf_cnpj, cliente.cpf_cnpj, cliente_id
        )

        usuario = await self._buscar_usuario_associado(cliente.usuario_id)

        self._aplicar_atualizacoes(cliente, usuario, command, email_limpo)

        cliente_salvo = await self.repository.salvar(cliente)
        return ClienteEditadoResponse.model_validate(cliente_salvo)

    async def _buscar_cliente_ou_404(self, cliente_id: UUID) -> Cliente:
        cliente = await self.repository.buscar_por_id(cliente_id)
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado."
            )
        return cliente

    def _higienizar_e_validar_email(self, email_raw: str | None) -> str | None:
        if email_raw is None:
            return None
        try:
            return Email(email_raw).valor
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"E-mail inválido: {str(exc)}",
            )

    async def _validar_conflitos_email(
        self,
        email_limpo: str | None,
        cliente_id: UUID,
        email_atual: str,
        usuario_id: UUID,
    ):
        if email_limpo is None or email_limpo == email_atual:
            return

        # Verifica conflito em Clientes
        query_cli = select(Cliente).where(
            Cliente.email == email_limpo, Cliente.id != cliente_id
        )
        res_cli = await self.repository.db.execute(query_cli)
        if res_cli.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="O e-mail informado já está em uso por outro cliente.",
            )

        # Verifica conflito em Usuários
        query_usr = select(Usuario).where(
            Usuario.email == email_limpo, Usuario.id != usuario_id
        )
        res_usr = await self.repository.db.execute(query_usr)
        if res_usr.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="O e-mail informado já está em uso por outro usuário.",
            )

    async def _validar_conflito_documento(
        self, cpf_cnpj_novo: str | None, cpf_cnpj_atual: str, cliente_id: UUID
    ):
        if not cpf_cnpj_novo or cpf_cnpj_novo == cpf_cnpj_atual:
            return

        cliente_existente = await self.repository.buscar_por_cpf_cnpj(cpf_cnpj_novo)
        if cliente_existente and cliente_existente.id != cliente_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe um cliente cadastrado com o documento informado.",
            )

    async def _buscar_usuario_associado(self, usuario_id: UUID) -> Usuario | None:
        query = select(Usuario).where(Usuario.id == usuario_id)
        result = await self.repository.db.execute(query)
        return result.scalar_one_or_none()

    def _aplicar_atualizacoes(
        self,
        cliente: Cliente,
        usuario: Usuario | None,
        command: EditarClienteRequest,
        email_limpo: str | None,
    ):
        if command.nome is not None:
            cliente.nome = command.nome
            if usuario:
                usuario.nome = command.nome

        if email_limpo is not None:
            cliente.email = email_limpo
            if usuario:
                usuario.email = email_limpo

        if command.telefone is not None:
            cliente.telefone = command.telefone

        if command.cpf_cnpj is not None:
            cliente.cpf_cnpj = command.cpf_cnpj

        if command.tipo_pessoa is not None:
            cliente.tipo_pessoa = command.tipo_pessoa
