from collections.abc import Sequence

from fastapi import Depends, HTTPException, status


from app.shared.security.schemas import UsuarioToken
from app.shared.security.dependencies import obter_usuario_atual
from app.shared.security.roles import Role


def requer_roles(roles_permitidas: Sequence[Role]):

    def verificar(
        usuario: UsuarioToken = Depends(obter_usuario_atual),
    ) -> UsuarioToken:

        if usuario.role not in roles_permitidas:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não possui permissão para acessar este recurso.",
            )

        return usuario

    return verificar
