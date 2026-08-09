from typing import Optional
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, ConfigDict


class CadastrarPecaRequest(BaseModel):
    """Schema de Entrada: Dados necessários para catalogar o insumo."""

    nome: str = Field(
        ..., min_length=2, max_length=100, description="Nome identificador da peça"
    )
    descricao: Optional[str] = Field(
        None, max_length=255, description="Descrição detalhada do item"
    )
    preco_custo: Decimal = Field(
        ..., gt=0, description="Preço de custo pago pelo insumo"
    )
    preco_venda: Decimal = Field(
        ..., gt=0, description="Preço de revenda cobrado na OS"
    )
    quantidade_inicial: int = Field(
        0, ge=0, description="Quantidade física inicial em estoque"
    )
    limite_minimo: int = Field(
        15, ge=0, description="Limite mínimo para disparo da política de compra"
    )

    @field_validator("preco_venda")
    @classmethod
    def validar_margem_lucro(cls, preco_venda: Decimal, info) -> Decimal:
        """Garante que a oficina não venda peças abaixo do preço de custo."""
        preco_custo = info.data.get("preco_custo")
        if preco_custo is not None and preco_venda < preco_custo:
            raise ValueError(
                "O preço de venda não pode ser inferior ao preço de custo."
            )
        return preco_venda


class PecaResponse(BaseModel):
    """Schema de Saída: Confirmação rica do item inserido no catálogo."""

    id: UUID
    nome: str
    descricao: Optional[str] = None
    quantidade_em_estoque: int
    preco_custo: Decimal
    preco_venda: Decimal
    limite_minimo: int
    precisa_recompra: bool

    model_config = ConfigDict(from_attributes=True)
