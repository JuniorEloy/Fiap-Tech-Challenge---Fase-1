import pytest
import base64
import json
import random
import string
from datetime import datetime, timedelta
from fastapi import status
from httpx import AsyncClient
from uuid import uuid4, UUID
from validate_docbr import CPF
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.usuarios.models import Usuario
from app.features.ordens_servico.models import (
    OrdemServico,
    StatusOS,
    OrdemServicoStatusLog,
)
from app.shared.utils.clock import DateTimeProvider


@pytest.mark.asyncio
async def test_gerente_deve_conseguir_acessar_relatorio_cliente_veiculo_com_sucesso(
    async_client: AsyncClient, token_gerente: str
):
    """
    Cenário: O Gerente solicita o relatório analítico de clientes e veículos.
    Resultado esperado: 200 OK com totais e veículos aninhados dentro de cada cliente correspondente.
    """
    headers = {"Authorization": f"Bearer {token_gerente}"}

    response = await async_client.get("/relatorio/cliente-veiculo", headers=headers)
    assert response.status_code == status.HTTP_200_OK

    body = response.json()
    assert "total_clientes" in body
    assert "total_veiculos" in body
    assert isinstance(body["clientes"], list)

    # 🌟 A validação agora atesta que veículos estão aninhados sob cada cliente!
    assert (
        "veiculos" not in body
    )  # Não deve mais existir uma chave flat "veiculos" na raiz

    for cliente in body["clientes"]:
        assert "id" in cliente
        assert "nome" in cliente
        assert "email" in cliente
        assert "telefone" in cliente
        assert "cpf_cnpj" in cliente
        assert "total_veiculos" in cliente
        assert "veiculos" in cliente
        assert isinstance(cliente["veiculos"], list)


@pytest.mark.asyncio
async def test_recepcionista_nao_deve_acessar_relatorio_do_gerente(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Recepcionista tenta ler o relatório analítico exclusivo de gerência.
    Resultado esperado: 403 Forbidden (Controle RBAC atuando adequadamente).
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}

    response = await async_client.get("/relatorio/cliente-veiculo", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def gerar_placa_valida_para_teste() -> str:
    """Gera uma placa Mercosul válida e aleatória (formato AAA9A99) para evitar colisões."""
    letras_aleatorias_1 = "".join(random.choices(string.ascii_uppercase, k=3))
    numero_1 = str(random.randint(0, 9))
    letra_aleatoria_2 = random.choice(string.ascii_uppercase)
    numeros_finais = "".join(random.choices(string.digits, k=2))
    return f"{letras_aleatorias_1}{numero_1}{letra_aleatoria_2}{numeros_finais}"


async def garantir_usuario_existe_no_banco(
    token: str, role: str, db: AsyncSession, uid: str
) -> str:
    """Decodifica o payload do JWT, obtém o sub (UUID) e insere fisicamente na tabela usuarios se não existir."""
    token_parts = token.split(".")
    payload_decoded = base64.b64decode(token_parts[1] + "==").decode("utf-8")
    payload_json = json.loads(payload_decoded)
    user_id = payload_json["sub"]

    res = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user_db = res.scalar_one_or_none()
    if not user_db:
        new_user = Usuario(
            id=UUID(user_id),
            nome=f"Usuario Teste {role.capitalize()} {uid}",
            email=f"{role.lower()}.{uid}@oficina.com",
            role=role,
            ativo=True,
        )
        db.add(new_user)
        await db.commit()
    return user_id


@pytest.mark.asyncio
async def test_gerente_deve_obter_relatorio_de_tempos_com_sucesso(
    async_client: AsyncClient,
    token_recepcionista: str,
    token_estoquista: str,
    token_mecanico: str,
    token_gerente: str,
    db: AsyncSession,
):
    """
    Cenário: Gerente acessa o painel executivo para avaliar a produtividade do pátio.
    Resultado esperado: 200 OK com os tempos operacionais e as médias calculadas deterministicamente.
    """
    headers_recep = {"Authorization": f"Bearer {token_recepcionista}"}
    headers_estoque = {"Authorization": f"Bearer {token_estoquista}"}
    headers_meca = {"Authorization": f"Bearer {token_mecanico}"}
    headers_gerente = {"Authorization": f"Bearer {token_gerente}"}

    uid = str(uuid4())[:6]

    # Garante usuários reais persistidos
    await garantir_usuario_existe_no_banco(
        token_recepcionista, "RECEPCIONISTA", db, uid
    )
    await garantir_usuario_existe_no_banco(token_estoquista, "ESTOQUISTA", db, uid)
    mecanico_id = await garantir_usuario_existe_no_banco(
        token_mecanico, "MECANICO", db, uid
    )
    await garantir_usuario_existe_no_banco(token_gerente, "GERENTE", db, uid)

    # 1. Cadastra Cliente e Veículo
    payload_cliente = {
        "nome": f"Aline Analitica {uid}",
        "email": f"aline.analitica.{uid}@gmail.com",
        "telefone": "11955554444",
        "cpf_cnpj": CPF().generate(),
        "tipo_pessoa": "FISICA",
    }
    res_cliente = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers_recep
    )
    assert res_cliente.status_code == status.HTTP_201_CREATED
    cliente_id = res_cliente.json()["id"]

    payload_veiculo = {
        "placa": gerar_placa_valida_para_teste(),
        "marca": "Chevrolet",
        "modelo": "Onix",
        "ano": 2020,
        "cliente_id": cliente_id,
    }
    res_veiculo = await async_client.post(
        "/veiculos", json=payload_veiculo, headers=headers_recep
    )
    assert res_veiculo.status_code == status.HTTP_201_CREATED
    veiculo_id = res_veiculo.json()["id"]

    # 2. Cadastra Serviço Base
    payload_servico = {
        "nome": f"Alinhamento e Balanceamento {uid}",
        "descricao": "Correção preventiva geométrica",
        "preco_mao_de_obra": 120.00,
        "duracao_estimada_minutos": 30,
        "permite_servico_expresso": False,
    }
    res_servico = await async_client.post(
        "/servicos", json=payload_servico, headers=headers_recep
    )
    servico_id = res_servico.json()["id"]

    # 3. Abre a OS na triagem (vazia, EM_DIAGNOSTICO)
    payload_os = {
        "cliente_id": cliente_id,
        "veiculo_id": veiculo_id,
        "servicos": [],
        "pecas": [],
    }
    res_os = await async_client.post(
        "/ordens-servico", json=payload_os, headers=headers_recep
    )
    os_id = res_os.json()["id"]

    # 4. Mecânico lança diagnóstico (transiciona para AGUARDANDO_APROVACAO)
    payload_diagnostico = {"servicos": [{"servico_id": servico_id}], "pecas": []}
    await async_client.put(
        f"/ordens-servico/{os_id}/diagnostico",
        json=payload_diagnostico,
        headers=headers_meca,
    )

    # 5. Recepcionista registra aprovação offline (transiciona para EM_EXECUCAO)
    payload_resposta = {"aprovado": True, "observacoes_cliente": "Aprovado!"}
    await async_client.post(
        f"/ordens-servico/{os_id}/resposta",
        json=payload_resposta,
        headers=headers_recep,
    )

    # 6. Mecânico finaliza a manutenção (transiciona para FINALIZADA)
    payload_finalizar = {"observacoes_finais": "Serviços executados com sucesso."}
    await async_client.post(
        f"/ordens-servico/{os_id}/finalizar",
        json=payload_finalizar,
        headers=headers_meca,
    )

    # --- SIMULAÇÃO DETERMINÍSTICA DE TIMESTAMPS NO BANCO ---
    # Vamos reidratar os timestamps da OS e dos logs de status para simular exatamente:
    # 15 mins em RECEBIDA
    # 45 mins em EM_DIAGNOSTICO
    # 60 mins em AGUARDANDO_APROVACAO
    # 90 mins em EM_EXECUCAO
    # Total Leadtime Full: 210 minutos. Leadtime Ativo: 150 minutos.
    clock = DateTimeProvider()
    agora = clock.agora()

    t0 = agora - timedelta(minutes=210)  # Abertura (RECEBIDA)
    t1 = agora - timedelta(minutes=195)  # Diagnóstico (EM_DIAGNOSTICO)
    t2 = agora - timedelta(minutes=150)  # Envio de Orçamento (AGUARDANDO_APROVACAO)
    t3 = agora - timedelta(minutes=90)  # Aprovação do Cliente (EM_EXECUCAO)
    t4 = agora  # Conclusão (FINALIZADA)

    db.expire_all()
    res_os_db = await db.execute(select(OrdemServico).where(OrdemServico.id == os_id))
    os_db = res_os_db.scalar_one()

    # Sobrescreve campos operacionais e KPIs desnormalizados de faturamento
    os_db.data_abertura = t0
    os_db.data_notificacao_cliente = t2
    os_db.data_resposta_cliente = t3
    os_db.data_conclusao = t4
    os_db.tempo_espera_aprovacao_minutos = 60
    os_db.leadtime_full_minutos = 210
    os_db.leadtime_ativo_minutos = 150

    # Sobrescreve as datas dos logs de transição de status de auditoria
    res_logs = await db.execute(
        select(OrdemServicoStatusLog).where(
            OrdemServicoStatusLog.ordem_servico_id == os_id
        )
    )
    logs = res_logs.scalars().all()

    for log in logs:
        if log.status_novo == StatusOS.EM_DIAGNOSTICO:
            log.data_transicao = t1
        elif log.status_novo == StatusOS.AGUARDANDO_APROVACAO:
            log.data_transicao = t2
        elif log.status_novo == StatusOS.EM_EXECUCAO:
            log.data_transicao = t3
        elif log.status_novo == StatusOS.FINALIZADA:
            log.data_transicao = t4

    await db.commit()

    # 7. Gerente consome o endpoint de tempos operacionais
    response = await async_client.get(
        "/relatorios/tempo_medio", headers=headers_gerente
    )
    assert response.status_code == status.HTTP_200_OK

    body = response.json()
    assert body["total_ordens_avaliadas"] >= 1
    assert body["tempo_medio_geral_minutos"] == 210
    assert body["tempo_medio_trabalho_ativo_minutos"] == 150
    assert body["tempo_medio_espera_aprovacao_minutos"] == 60

    # Valida detalhamento refinado de tempos por etapa operacional
    detalhes_etapas = body["tempo_medio_por_etapa_minutos"]
    assert detalhes_etapas["RECEBIDA"] == 15
    assert detalhes_etapas["EM_DIAGNOSTICO"] == 45
    assert detalhes_etapas["AGUARDANDO_APROVACAO"] == 60
    assert detalhes_etapas["EM_EXECUCAO"] == 90


@pytest.mark.asyncio
async def test_mecanico_nao_deve_conseguir_acessar_relatorio_de_tempos(
    async_client: AsyncClient, token_mecanico: str
):
    """
    Cenário: Mecânico tenta acessar o painel executivo de tempos do pátio (violação de segurança).
    Resultado esperado: 403 Forbidden.
    """
    headers = {"Authorization": f"Bearer {token_mecanico}"}
    response = await async_client.get("/relatorios/tempo_medio", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_usuario_nao_autenticado_deve_receber_401(async_client: AsyncClient):
    """
    Cenário: Requisição ao painel de relatórios sem cabeçalho JWT Bearer.
    Resultado esperado: 401 Unauthorized.
    """
    response = await async_client.get("/relatorios/tempo_medio")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
