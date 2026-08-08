from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
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


class UsuarioEditadoResponse(BaseModel):
    """Schema de Saída: Confirmação rica do operador pós-edição."""

    id: UUID
    nome: str
    email: EmailStr
    role: Role
    ativo: bool

    class Config:
        from_attributes = True
