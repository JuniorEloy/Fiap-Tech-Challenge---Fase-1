from typing import List, Sequence
from uuid import UUID
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.shared.security.roles import Role
from app.shared.security.schemas import UsuarioToken
from app.shared.security.tokens import decodificar_token

# Integração nativa do Swagger UI com o endpoint de login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def obter_usuario_atual(
    token: str = Depends(oauth2_scheme),
) -> UsuarioToken:
    """
    Extrai o token JWT enviado no cabeçalho Authorization e converte
    no objeto fortemente tipado UsuarioToken.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Access Token inválido ou expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decodificar_token(token)

        if not payload or payload.get("type") != "access":
            raise credentials_exception

        return UsuarioToken(
            id=UUID(payload["sub"]),
            role=Role(payload["role"]),
            jti=UUID(payload["jti"]),
        )

    except (
        jwt.ExpiredSignatureError,
        jwt.InvalidAudienceError,
        jwt.InvalidIssuerError,
        jwt.InvalidSignatureError,
        jwt.InvalidTokenError,
        ValueError,
        KeyError,
    ):
        raise credentials_exception


def requer_roles(roles_permitidas: Sequence[Role]):
    """Valida se a role do usuário no JWT tem permissão para acessar o endpoint."""

    async def verificador(
        usuario_atual: UsuarioToken = Depends(obter_usuario_atual),
    ) -> UsuarioToken:
        if usuario_atual.role not in roles_permitidas:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado: Perfil sem permissão para esta ação.",
            )
        return usuario_atual

    return verificador


def validar_propriedade_ou_role(
    resource_owner_id: UUID,
    usuario_atual: UsuarioToken,
    roles_bypass: Sequence[Role] | None = None,
) -> None:
    """
    Previne IDOR (Insecure Direct Object Reference):
    Garante que o cliente logado só visualize/edite seus próprios recursos,
    a menos que possua uma Role administrativa (ex: Gerente/Recepcionista).
    """
    roles_bypass = roles_bypass or [Role.GERENTE, Role.RECEPCIONISTA]

    if usuario_atual.id != resource_owner_id and usuario_atual.role not in roles_bypass:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: Você não tem permissão para acessar o recurso de outro usuário.",
        )
