from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class DesativarServicoResponse(BaseModel):
    """Schema de Saida: Confirmacao rica de desativacao de servico."""

    servico_id: UUID = Field(..., description="ID do servico desativado")
    nome: str = Field(..., description="Nome do servico desativado")
    ativo: bool = Field(
        False, description="Confirmado como False pos desativacao logica"
    )
    mensagem: str = Field(..., description="Mensagem descritiva do resultado da acao")

    model_config = ConfigDict(from_attributes=True)
