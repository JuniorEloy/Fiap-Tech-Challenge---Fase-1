from enum import Enum
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, AliasPath
from app.features.ordens_servico.models import StatusOS


class FormaPagamento(str, Enum):
    DINHEIRO = "DINHEIRO"
    DEBITO = "DEBITO"
    CREDITO = "CREDITO"
    PIX = "PIX"


class RegistrarEntregaRequest(BaseModel):
    """Schema de Entrada: Registro de pagamento e autorização de saída do veículo."""

    forma_pagamento: FormaPagamento = Field(
        ..., description="Meio de pagamento utilizado pelo cliente no caixa"
    )
    quantidade_parcelas: int = Field(
        1, ge=1, le=12, description="Número de parcelas (relevante apenas para CREDITO)"
    )
    comprovante_transacao: Optional[str] = Field(
        None,
        max_length=100,
        description="Código de autorização da maquininha ou ID da transação PIX",
    )


class ItemServicoResponse(BaseModel):
    """Schema de Saída: Representação do serviço com congelamento de preço histórico."""

    servico_id: UUID = Field(validation_alias="servico_base_id")
    nome: str = Field(validation_alias=AliasPath("servico_base", "nome"))
    preco_applied: Decimal = Field(validation_alias="preco_aplicado")
    duracao_minutos: int

    model_config = ConfigDict(from_attributes=True)


class ItemPecaResponse(BaseModel):
    """Schema de Saída: Representação de peças com congelamento de preços de venda."""

    peca_id: UUID
    nome_peca: str = Field(validation_alias=AliasPath("peca", "nome"))
    quantidade: int
    preco_unitario: Decimal = Field(validation_alias="preco_unitario_aplicado")

    model_config = ConfigDict(from_attributes=True)


class EntregaOSResponse(BaseModel):
    """Schema de Saída: Confirmação rica da entrega e faturamento encerrado."""

    id: UUID
    cliente_id: UUID
    veiculo_id: UUID
    status: StatusOS
    visualizacao_hash: UUID

    data_abertura: datetime
    data_conclusao: Optional[datetime] = None

    # Detalhes do Pagamento
    forma_pagamento: Optional[FormaPagamento] = None
    comprovante_transacao: Optional[str] = None

    # Consolidação Financeira
    valor_total_servicos: Decimal = Field(default=Decimal("0.00"))
    valor_total_pecas: Decimal = Field(default=Decimal("0.00"))
    valor_total_os: Decimal = Field(default=Decimal("0.00"))

    itens_servico: List[ItemServicoResponse] = Field(default_factory=list)
    itens_peca: List[ItemPecaResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
