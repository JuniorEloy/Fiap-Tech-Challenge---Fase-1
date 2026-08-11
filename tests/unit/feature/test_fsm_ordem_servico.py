import pytest
from datetime import datetime, timedelta
from uuid import uuid7
from app.features.ordem_servico.models import (
    OrdemServico,
    StatusOS,
    OrdemServicoStatusLog,
)


def test_deve_permitir_transicao_valida_de_status():
    os = OrdemServico(
        id=uuid7(), cliente_id=uuid7(), veiculo_id=uuid7(), status=StatusOS.RECEBIDA
    )
    operador_id = uuid7()

    # Transição de RECEBIDA -> EM_DIAGNOSTICO é válida!
    log = os.alterar_status(StatusOS.EM_DIAGNOSTICO, operador_id)

    assert os.status == StatusOS.EM_DIAGNOSTICO
    assert log.status_anterior == StatusOS.RECEBIDA
    assert log.status_novo == StatusOS.EM_DIAGNOSTICO
    assert log.operador_id == operador_id


def test_deve_lancar_erro_para_transicao_ilegal_de_status():
    os = OrdemServico(
        id=uuid7(), cliente_id=uuid7(), veiculo_id=uuid7(), status=StatusOS.RECEBIDA
    )
    operador_id = uuid7()

    # É expressamente ilegal ir de RECEBIDA direto para FINALIZADA
    with pytest.raises(ValueError) as excinfo:
        os.alterar_status(StatusOS.FINALIZADA, operador_id)

    assert "Transição física ilegal de status" in str(excinfo.value)
    assert os.status == StatusOS.RECEBIDA


def test_deve_calcular_tempo_de_espera_do_cliente_ao_responder_orcamento():
    os = OrdemServico(
        id=uuid7(), cliente_id=uuid7(), veiculo_id=uuid7(), status=StatusOS.RECEBIDA
    )
    operador_id = uuid7()

    # 1. Envia para Aprovação (Simula geração de orçamento e disparo WhatsApp)
    os.alterar_status(StatusOS.AGUARDANDO_APROVACAO, operador_id)
    assert os.data_notificacao_cliente is not None

    # Mockando a data de notificação para 30 minutos no passado
    os.data_notificacao_cliente = datetime.utcnow() - timedelta(minutes=30)

    # 2. Cliente aprova o orçamento e o status move para EM_EXECUCAO
    os.alterar_status(StatusOS.EM_EXECUCAO, operador_id)

    assert os.data_resposta_cliente is not None
    assert os.tempo_espera_aprovacao_minutos == 30


def test_deve_calcular_lead_times_ao_finalizar_a_os():
    abertura = datetime.utcnow() - timedelta(hours=10)  # Carro entrou há 10 horas
    os = OrdemServico(
        id=uuid7(),
        cliente_id=uuid7(),
        veiculo_id=uuid7(),
        data_abertura=abertura,
        status=StatusOS.EM_EXECUCAO,
        tempo_espera_aprovacao_minutos=120,  # Cliente levou 2 horas para aprovar
    )
    operador_id = uuid7()

    # Finaliza os serviços
    os.alterar_status(StatusOS.FINALIZADA, operador_id)

    assert os.data_conclusao is not None
    # 10 horas = 600 minutos
    assert os.leadtime_full_minutos >= 600
    # Leadtime ativo = 600 total - 120 de espera do cliente = 480 minutos de trabalho ativo
    assert os.leadtime_ativo_minutos >= 480
