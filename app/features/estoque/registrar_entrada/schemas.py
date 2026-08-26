from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class RegistrarEntradaRequest(BaseModel):
    """Schema de Entrada: Dados para o reabastecimento físico de peças no estoque."""

    peca_id: UUID = Field(..., description="ID único da peça/insumo")
    quantidade: int = Field(
        ..., gt=0, description="Quantidade a ser adicionada (deve ser maior que zero)"
    )


class RegistroEntradaResponse(BaseModel):
    """Schema de Saída: Confirmação rica da entrada física de materiais."""

    peca_id: UUID
    nome: str
    quantidade_adicionada: int
    saldo_anterior: int
    saldo_atual: int
    limite_minimo: int
    precisa_recompra: bool = Field(
        ...,
        description="Atualizado pelo domínio após a entrada. Se o novo saldo for >= 15, será False.",
    )

    model_config = ConfigDict(from_attributes=True)
