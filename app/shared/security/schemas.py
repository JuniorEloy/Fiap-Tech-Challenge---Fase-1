from uuid import UUID
from pydantic import BaseModel
from app.shared.security.roles import Role


class UsuarioToken(BaseModel):
    """Representa a identidade e permissões extraídas do JWT autenticado (Stateless)."""

    id: UUID
    role: Role
    jti: UUID
