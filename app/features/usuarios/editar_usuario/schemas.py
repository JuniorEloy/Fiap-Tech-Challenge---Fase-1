from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.shared.domain.value_objects.email import Email
from app.shared.security.roles import Role


class EditarUsuarioRequest(BaseModel):
    """Schema de Entrada: Dados permitidos para alteração cadastral do operador."""

    nome: Optional[str] = Field(
        None, min_length=3, max_length=150, description="Nome completo"
    )
    email: Optional[EmailStr] = Field(None, description="E-mail funcional exclusivo")
    senha: Optional[str] = Field(
        None, min_length=6, description="Nova senha de acesso (opcional)"
    )
    role: Optional[Role] = Field(None, description="Novo papel administrativo")
    ativo: Optional[bool] = Field(
        None, description="Status de ativação para bloqueio de acessos"
    )

    @field_validator("email")
    @classmethod
    def validar_email(cls, v: str) -> str:
        # Usa o VO para validar a entrada e já higieniza (retorna limpo)
        return Email(v).valor


class UsuarioEditadoResponse(BaseModel):
    """Schema de Saída: Confirmação rica do operador pós-edição."""

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
