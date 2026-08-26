from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class ExcluirUsuarioResponse(BaseModel):
    """Schema de Saida: Confirmacao rica da inativacao (Soft Delete) do usuario."""

    usuario_id: UUID = Field(..., description="ID do usuario inativado")
    nome: str = Field(..., description="Nome do usuario inativado")
    ativo: bool = Field(
        False, description="Estado de ativacao do usuario (sempre False apos inativar)"
    )
    mensagem: str = Field(..., description="Mensagem de sucesso da inativacao")

    model_config = ConfigDict(from_attributes=True)
