from uuid import UUID
from fastapi import HTTPException, status
from app.features.usuarios.repository import UsuarioRepository
from app.features.usuarios.excluir_usuario.schemas import ExcluirUsuarioResponse


class ExcluirUsuarioHandler:
    def __init__(self, repository: UsuarioRepository):
        self.repository = repository

    async def executar(self, id: UUID, executor_id: UUID) -> ExcluirUsuarioResponse:
        usuario = await self.repository.buscar_por_id(id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operador nao encontrado no sistema.",
            )

        if usuario.id == executor_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nao e permitido inativar a si proprio no sistema.",
            )

        await self.repository.inativar(usuario)
        await self.repository.db.commit()

        return ExcluirUsuarioResponse(
            usuario_id=usuario.id,
            nome=usuario.nome,
            ativo=False,
            mensagem=f"O operador '{usuario.nome}' foi desativado com sucesso (Soft Delete).",
        )
