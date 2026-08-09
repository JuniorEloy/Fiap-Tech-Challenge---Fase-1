from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class BaixarEstoqueRequest(BaseModel):
    """Schema de Entrada: Dados para a retirada física de peças do almoxarifado."""

    peca_id: UUID = Field(..., description="ID único da peça/insumo")
    quantidade: int = Field(
        ..., gt=0, description="Quantidade a ser retirada (deve ser maior que zero)"
    )


class BaixaEstoqueResponse(BaseModel):
    """Schema de Saída: Confirmação rica da movimentação de estoque."""

    peca_id: UUID
    nome: str
    quantidade_retirada: int
    saldo_restante: int
    limite_minimo: int
    precisa_recompra: bool = Field(
        ...,
        description="True se o saldo restante ficou abaixo do limite mínimo de segurança (15 itens)",
    )

    model_config = ConfigDict(from_attributes=True)
