from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.shared.security.roles import Role
from app.shared.domain.value_objects.email import Email


class CriarUsuarioRequest(BaseModel):
    """Schema de Entrada: Dados necessários para criar o operador."""

    nome: str = Field(..., min_length=3, max_length=150, description="Nome completo")
    email: EmailStr = Field(..., description="E-mail funcional exclusivo")
    senha: str = Field(..., min_length=6, description="Senha segura de acesso")
    role: Role = Field(..., description="Papel administrativo")

    @field_validator("email")
    @classmethod
    def validar_email(cls, v: str) -> str:
        # Usa o VO para validar a entrada e já higieniza (retorna limpo)
        return Email(v).valor


class UsuarioResponse(BaseModel):
    """Schema de Saída: Dados expostos após a criação."""

    id: UUID
    nome: str
    email: EmailStr
    role: Role

    @field_validator("email")
    @classmethod
    def validar_email(cls, v: str) -> str:
        # Usa o VO para validar a entrada e já higieniza (retorna limpo)
        return Email(v).valor

    class Config:
        from_attributes = True  # Permite mapear diretamente do model Usuario
