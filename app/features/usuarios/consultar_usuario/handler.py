from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.usuarios.models import Usuario
from app.features.usuarios.consultar_usuario.schemas import ConsultarUsuarioResponse


class ConsultarUsuarioHandler:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def executar(self, usuario_id: UUID) -> ConsultarUsuarioResponse:
        """
        Executa a consulta detalhada de um operador:
        1. Busca o usuário no banco pelo ID.
        2. Retorna os dados estruturados no DTO correspondente.
        3. Caso o ID não exista, lança uma exceção 404 Not Found.
        """
        result = await self.db.execute(select(Usuario).where(Usuario.id == usuario_id))
        usuario = result.scalar_one_or_none()

        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado."
            )

        return ConsultarUsuarioResponse.model_validate(usuario)