from abc import ABC, abstractmethod
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field


class TransacaoResultado(BaseModel):
    sucesso: bool = Field(..., description="Status do processamento do pagamento")
    transacao_id: str = Field(..., description="ID gerado pelo gateway de pagamento")
    mensagem: str = Field(..., description="Detalhe de retorno da transação")


class GatewayPagamentoPort(ABC):
    @abstractmethod
    async def processar_pagamento(
        self, ordem_servico_id: UUID, valor: Decimal, token_cartao: str
    ) -> TransacaoResultado:
        """
        Dispara transações financeiras síncronas contra o provedor de cartões.
        """
        pass
