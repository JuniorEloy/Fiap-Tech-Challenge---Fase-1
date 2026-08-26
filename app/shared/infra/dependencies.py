from app.shared.domain.ports.notificacao import EnviadorNotificacaoPort
from app.shared.infra.adapters.whatsapp_mock import WhatsAppConsoleAdapter

from app.shared.domain.ports.pagamento import GatewayPagamentoPort
from app.shared.infra.adapters.pagamento_mock import PaymentGatewayMockAdapter


def obter_notificador_whatsapp() -> EnviadorNotificacaoPort:
    """Retorna o adaptador ativo do WhatsApp (pode alternar via env)."""
    return WhatsAppConsoleAdapter()


def obter_gateway_pagamento() -> GatewayPagamentoPort:
    """Retorna o adaptador ativo de gateway de pagamento."""
    return PaymentGatewayMockAdapter()
