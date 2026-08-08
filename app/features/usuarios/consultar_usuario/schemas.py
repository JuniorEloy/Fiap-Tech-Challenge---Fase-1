from uuid import UUID
from pydantic import BaseModel, EmailStr
from app.shared.security.roles import Role


class ConsultarUsuarioResponse(BaseModel):
    """Schema de Saída: Dados detalhados retornados na consulta do operador."""

    id: UUID
    nome: str
    email: EmailStr
    role: Role
    ativo: bool

    class Config:
        from_attributes = True
