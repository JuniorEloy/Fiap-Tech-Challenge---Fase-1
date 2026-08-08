from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from app.shared.security.roles import Role


class CriarUsuarioRequest(BaseModel):
    """Schema de Entrada: Dados necessários para criar o operador."""

    nome: str = Field(..., min_length=3, max_length=150, description="Nome completo")
    email: EmailStr = Field(..., description="E-mail funcional exclusivo")
    senha: str = Field(..., min_length=6, description="Senha segura de acesso")
    role: Role = Field(..., description="Papel administrativo")


class UsuarioResponse(BaseModel):
    """Schema de Saída: Dados expostos após a criação."""

    id: UUID
    nome: str
    email: EmailStr
    role: Role

    class Config:
        from_attributes = True  # Permite mapear diretamente do model Usuario
