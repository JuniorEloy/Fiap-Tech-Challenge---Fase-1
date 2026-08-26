from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class ExcluirVeiculoResponse(BaseModel):
    """Schema de Saida: Confirmacao rica da exclusao de um veiculo."""

    veiculo_id: UUID = Field(..., description="ID do veiculo removido")
    placa: str = Field(..., description="Placa do veiculo removido")
    mensagem: str = Field(..., description="Mensagem de sucesso da remocao")

    model_config = ConfigDict(from_attributes=True)
