import hashlib
import secrets
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid7
import jwt
from app.shared.utils.clock import DateTimeProvider

from app.config import settings
from app.shared.security.roles import Role


def gerar_hash_token(token: str) -> str:
    """Retorna o SHA-256 do Refresh Token."""
    return hashlib.sha256(token.encode()).hexdigest()


def criar_refresh_token_bruto() -> tuple[str, str]:
    """
    Retorna:
        token_bruto -> enviado ao cliente
        token_hash -> salvo no banco
    """
    token_bruto = secrets.token_urlsafe(64)
    return token_bruto, gerar_hash_token(token_bruto)


def criar_access_token(usuario_id: UUID, role: Role) -> str:
    agora = DateTimeProvider().agora()

    payload = {
        "sub": str(usuario_id),
        "role": role.value,
        "type": "access",
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": agora,
        "nbf": agora,
        "exp": agora + timedelta(minutes=15),
        "jti": str(uuid7()),
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decodificar_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_AUDIENCE,
        leeway=5,
        options={
            "require": [
                "sub",
                "role",
                "type",
                "iss",
                "aud",
                "iat",
                "nbf",
                "exp",
                "jti",
            ]
        },
    )
