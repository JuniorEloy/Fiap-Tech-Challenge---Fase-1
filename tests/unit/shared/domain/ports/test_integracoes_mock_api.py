# tests/unit/domain/ports/test_integracoes_mock_api.py
import pytest
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4
from decimal import Decimal

# Importando Portas e Adaptadores simulados
from app.shared.domain.ports.notificacao import EnviadorNotificacaoPort
from app.shared.infra.adapters.whatsapp_mock import WhatsAppConsoleAdapter

from app.shared.domain.ports.pagamento import GatewayPagamentoPort, TransacaoResultado
from app.shared.infra.adapters.pagamento_mock import PaymentGatewayMockAdapter


# =============================================================================
# 1. TESTES DE UNIDADE: ADAPTADOR DE WHATSAPP (CONSOLE)
# =============================================================================


@pytest.mark.asyncio
async def test_notificador_whatsapp_deve_enviar_link_de_aprovacao_com_sucesso():
    """
    Cenário: Solicitação de envio de link de aprovação para orçamento.
    Resultado esperado: Retorno True com formatação correta de texto e link público.
    """
    adaptador = WhatsAppConsoleAdapter()
    telefone = "11999998888"
    nome = "Carlos Alberto"
    hash_os = uuid4()
    valor = Decimal("450.50")

    resultado = await adaptador.enviar_link_aprovacao(
        telefone=telefone,
        cliente_nome=nome,
        visualizacao_hash=hash_os,
        valor_total=valor,
    )

    assert resultado is True


@pytest.mark.asyncio
async def test_notificador_whatsapp_deve_enviar_aviso_de_conclusao_com_sucesso():
    """
    Cenário: Solicitação de aviso de carro pronto para o cliente.
    Resultado esperado: Retorno True informando placa do veículo.
    """
    adaptador = WhatsAppConsoleAdapter()
    telefone = "11977776666"
    nome = "Mariana Silva"
    placa = "KPG2J45"

    resultado = await adaptador.enviar_notificacao_conclusao(
        telefone=telefone, cliente_nome=nome, placa=placa
    )

    assert resultado is True


# =============================================================================
# 2. TESTES DE UNIDADE: ADAPTADOR DE PAGAMENTO (MOCK)
# =============================================================================


@pytest.mark.asyncio
async def test_gateway_pagamento_deve_autorizar_transacao_com_sucesso():
    """
    Cenário: Envio de dados normais de pagamento (cartão válido).
    Resultado esperado: Sucesso=True com ID de transação autorizado gerado pelo gateway.
    """
    gateway = PaymentGatewayMockAdapter()
    os_id = uuid4()
    valor = Decimal("1250.00")
    token_cartao = "tok_visa_valid_card"

    resultado = await gateway.processar_pagamento(
        ordem_servico_id=os_id, valor=valor, token_cartao=token_cartao
    )

    assert isinstance(resultado, TransacaoResultado)
    assert resultado.sucesso is True
    assert resultado.transacao_id.startswith("txn_pay_")
    assert "autorizado com sucesso" in resultado.mensagem


@pytest.mark.asyncio
async def test_gateway_pagamento_deve_recusar_transacao_com_cartao_9999():
    """
    Cenário: Processamento com cartão contendo os dígitos de falha simulados '9999'.
    Resultado esperado: Sucesso=False com mensagem de saldo insuficiente.
    """
    gateway = PaymentGatewayMockAdapter()
    os_id = uuid4()
    valor = Decimal("320.00")
    token_cartao = "tok_master_ending_in_9999_insufficient_funds"

    resultado = await gateway.processar_pagamento(
        ordem_servico_id=os_id, valor=valor, token_cartao=token_cartao
    )

    assert isinstance(resultado, TransacaoResultado)
    assert resultado.sucesso is False
    assert resultado.transacao_id.startswith("txn_fail_")
    assert "Saldo Insuficiente" in resultado.mensagem


# =============================================================================
# 3. TESTES DE CONTRATO / COMPORTAMENTO DO HANDLER USANDO MOCKS (DIP)
# =============================================================================


@pytest.mark.asyncio
async def test_handler_deve_consumir_as_portas_e_validar_o_processamento_completo():
    """
    Cenário: Simula um caso de uso de faturamento que depende de ambas as portas.
    Comprova que o design do software suporta injeção de dependência e desacoplamento de infra.
    """
    # 1. Cria Mocks baseados no contrato estrito das portas abstratas
    mock_notificador = MagicMock(spec=EnviadorNotificacaoPort)
    mock_notificador.enviar_notificacao_conclusao = AsyncMock(return_value=True)

    mock_gateway = MagicMock(spec=GatewayPagamentoPort)
    mock_gateway.processar_pagamento = AsyncMock(
        return_value=TransacaoResultado(
            sucesso=True,
            transacao_id="txn_pay_unit_test_123",
            mensagem="Sucesso em testes.",
        )
    )

    # 2. Executa chamada simulada contra as portas
    res_pag = await mock_gateway.processar_pagamento(
        ordem_servico_id=uuid4(), valor=Decimal("200.00"), token_cartao="token_teste"
    )

    assert res_pag.sucesso is True

    # 3. Comprova se o disparo da notificação foi efetuado corretamente
    res_not = await mock_notificador.enviar_notificacao_conclusao(
        telefone="11955554444", cliente_nome="Marcos Lima", placa="ABC1D23"
    )

    assert res_not is True

    # Valida as interações simuladas das portas síncronas do DDD
    mock_gateway.processar_pagamento.assert_called_once()
    mock_notificador.enviar_notificacao_conclusao.assert_called_once_with(
        telefone="11955554444", cliente_nome="Marcos Lima", placa="ABC1D23"
    )
