from typing import Optional
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class PecaEstoqueBaixoDTO(BaseModel):
    """Representa um item do estoque que precisa de atenção e recompra."""

    id: UUID
    nome: str
    quantidade_em_estoque: int
    limite_minimo: int
    unidades_em_falta: int  # Diferença absoluta para atingir o limite seguro
    preco_custo_referencia: Decimal
    capital_necessario_reposicao: Decimal  # unidades_em_falta * preco_custo

    model_config = ConfigDict(from_attributes=True)


class RelatorioEstoqueBaixoResponse(BaseModel):
    """Schema de resposta consolidado com os itens pendentes e resumo financeiro."""

    total_itens_criticos: int
    custo_total_estimado_reposicao: Decimal
    itens: list[PecaEstoqueBaixoDTO]

    model_config = ConfigDict(from_attributes=True)
