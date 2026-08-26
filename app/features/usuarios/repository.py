from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.usuarios.models import Usuario


class UsuarioRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def buscar_por_email(self, email: str) -> Usuario | None:
        """Busca um usuário ativo na base usando o e-mail."""
        result = await self.db.execute(select(Usuario).where(Usuario.email == email))
        return result.scalar_one_or_none()

    async def salvar(self, usuario: Usuario) -> Usuario:
        """Persiste um usuário no banco e retorna a instância atualizada."""
        self.db.add(usuario)
        await self.db.commit()
        await self.db.refresh(usuario)
        return usuario

    async def buscar_por_id(self, id: UUID) -> Usuario | None:
        stmt = select(Usuario).where(Usuario.id == id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def inativar(self, usuario: Usuario) -> None:
        """
        Executa a exclusao logica (Soft Delete) do operador no sistema.
        """
        usuario.ativo = False
        self.db.add(usuario)
        await self.db.flush() 
