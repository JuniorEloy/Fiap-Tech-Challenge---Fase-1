from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class ExcluirPecaResponse(BaseModel):
    """Schema de Saida: Confirmacao rica da exclusao de uma peca."""

    peca_id: UUID = Field(..., description="ID da peca removida")
    nome: str = Field(..., description="Nome da peca removida")
    mensagem: str = Field(..., description="Mensagem de sucesso da remocao")

    model_config = ConfigDict(from_attributes=True)
