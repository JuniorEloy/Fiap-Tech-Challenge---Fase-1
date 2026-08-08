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


class EditarUsuarioHandler:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def executar(
        self, usuario_id: UUID, command: EditarUsuarioRequest
    ) -> UsuarioEditadoResponse:
        """
        Executa as validações e persiste as modificações no operador:
        1. Busca o usuário pelo ID.
        2. Valida se o novo e-mail já está em uso por outra conta.
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

        # 2. Se o e-mail foi alterado, garante unicidade absoluta na base
        if command.email and command.email != usuario.email:
            email_conflict_query = select(Usuario).where(
                Usuario.email == command.email, Usuario.id != usuario_id
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

        if command.email is not None:
            usuario.email = command.email

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
