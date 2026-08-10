from typing import Sequence
from uuid import UUID
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated

from app.shared.security.roles import Role
from app.shared.security.schemas import UsuarioToken
from app.shared.security.tokens import decodificar_token

security_scheme = HTTPBearer(auto_error=False)


def obter_usuario_atual(
    token_auth: Annotated[
        HTTPAuthorizationCredentials | None, Depends(security_scheme)
    ],
) -> UsuarioToken:
    """
    Extrai o token JWT enviado no cabeçalho Authorization e converte
    no objeto fortemente tipado UsuarioToken de forma síncrona.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Access Token inválido ou expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token_auth:
        raise credentials_exception

    try:
        token_bruto = token_auth.credentials
        payload = decodificar_token(token_bruto)

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

    def verificador(
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
