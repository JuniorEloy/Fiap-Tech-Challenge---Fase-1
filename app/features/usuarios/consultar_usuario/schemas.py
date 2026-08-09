from uuid import UUID
from pydantic import BaseModel, EmailStr, field_validator
from app.shared.security.roles import Role
from app.shared.domain.value_objects.email import Email


class ConsultarUsuarioResponse(BaseModel):
    """Schema de Saída: Dados detalhados retornados na consulta do operador."""

    id: UUID
    nome: str
    email: EmailStr
    role: Role
    ativo: bool

    @field_validator("email")
    @classmethod
    def validar_email(cls, v: str) -> str:
        # Usa o VO para validar a entrada e já higieniza (retorna limpo)
        return Email(v).valor

    class Config:
        from_attributes = True
