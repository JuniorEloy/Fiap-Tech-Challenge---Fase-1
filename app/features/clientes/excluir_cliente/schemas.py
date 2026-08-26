from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class ExcluirClienteResponse(BaseModel):
    """Schema de Saida: Confirmacao rica da exclusao de um cliente."""

    cliente_id: UUID = Field(..., description="ID do cliente removido")
    nome: str = Field(..., description="Nome do cliente removido")
    mensagem: str = Field(..., description="Mensagem de sucesso da remocao")

    model_config = ConfigDict(from_attributes=True)
