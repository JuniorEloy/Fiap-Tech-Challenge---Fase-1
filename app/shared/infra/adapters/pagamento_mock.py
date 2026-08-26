from decimal import Decimal
from uuid import UUID, uuid7
from app.shared.domain.ports.pagamento import GatewayPagamentoPort, TransacaoResultado


class PaymentGatewayMockAdapter(GatewayPagamentoPort):
    async def processar_pagamento(
        self, ordem_servico_id: UUID, valor: Decimal, token_cartao: str
    ) -> TransacaoResultado:
        """
        Processamento simulado:
        - Cartões contendo '9999' simulam transações recusadas (Ex: saldo insuficiente).
        - Demais cartões são processados e faturados com absoluto sucesso.
        """
        if "9999" in token_cartao:
            return TransacaoResultado(
                sucesso=False,
                transacao_id="txn_fail_" + uuid7().hex[:8],
                mensagem="Transação recusada pela operadora de cartão: Saldo Insuficiente.",
            )

        return TransacaoResultado(
            sucesso=True,
            transacao_id="txn_pay_" + uuid7().hex[:8],
            mensagem="Pagamento autorizado com sucesso pelo gateway de testes.",
        )
