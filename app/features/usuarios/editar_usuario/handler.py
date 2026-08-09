from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.usuarios.models import Usuario
from app.features.usuarios.editar_usuario.schemas import (
    EditarUsuarioRequest,
    UsuarioEditadoResponse,
)
from app.shared.security.password import gerar_hash_senha
from app.shared.domain.value_objects.email import Email


class EditarUsuarioHandler:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def executar(
        self, usuario_id: UUID, command: EditarUsuarioRequest
    ) -> UsuarioEditadoResponse:
        """
        Executa as validações e persiste as modificações no operador:
        1. Busca o usuário pelo ID.
        2. Valida e-mail estruturalmente com o VO Email e garante unicidade.
        3. Realiza a criptografia segura da nova senha (se enviada).
        4. Grava as alterações no banco de dados.
        """
        # 1. Recupera o operador cadastrado
        result = await self.db.execute(select(Usuario).where(Usuario.id == usuario_id))
        usuario = result.scalar_one_or_none()

        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado."
            )

        # 2. Se o e-mail foi enviado no payload, valida e normaliza usando o Value Object
        email_limpo = None
        if command.email is not None:
            try:
                # O construtor do VOEmail aplica .lower().strip() e valida a estrutura
                email_limpo = Email(command.email).valor
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"E-mail inválido: {str(exc)}",
                )

        # Garante unicidade absoluta na base usando o e-mail higienizado
        if email_limpo is not None and email_limpo != usuario.email:
            email_conflict_query = select(Usuario).where(
                Usuario.email == email_limpo, Usuario.id != usuario_id
            )
            conflict_res = await self.db.execute(email_conflict_query)
            if conflict_res.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Já existe um usuário cadastrado com este e-mail.",
                )

        # 3. Atualização condicional e segura de campos
        if command.nome is not None:
            usuario.nome = command.nome

        if email_limpo is not None:
            usuario.email = email_limpo

        if command.senha is not None:
            usuario.senha_hash = gerar_hash_senha(command.senha)

        if command.role is not None:
            usuario.role = command.role

        if command.ativo is not None:
            usuario.ativo = command.ativo

        # 4. Commit e atualização da sessão do SQLAlchemy
        await self.db.commit()
        await self.db.refresh(usuario)

        return UsuarioEditadoResponse.model_validate(usuario)
