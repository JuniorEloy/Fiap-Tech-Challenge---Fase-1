# tests/integration/features/test_abertura_os_api.py
import pytest
from fastapi import status
from httpx import AsyncClient
from uuid import uuid7
from validate_docbr import CPF
import random
import string

# 🌟 Testes de Integração de API com suporte completo a RBAC (Fase 1 - Etapa 2)
# Utiliza as fixtures oficiais configuradas em seu conftest.py para simular
# autenticação real de cada papel do sistema.

def gerar_placa_valida_para_teste() -> str:
    """Gera uma placa Mercosul válida e aleatória (formato AAA9A99) para evitar colisões."""
    leiras_aleatorias_1 = "".join(random.choices(string.ascii_uppercase, k=3))
    numero_1 = str(random.randint(0, 9))
    letra_aleatoria_2 = random.choice(string.ascii_uppercase)
    numeros_finais = "".join(random.choices(string.digits, k=2))
    
    return f"{leiras_aleatorias_1}{numero_1}{letra_aleatoria_2}{numeros_finais}"


@pytest.mark.asyncio
async def test_recepcionista_deve_abrir_os_com_sucesso_em_diagnostico_quando_nao_houver_servicos(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Recepcionista tenta abrir uma OS padrão sem serviços pré-definidos (ex: "carro falhando").
    Resultado esperado: 201 Created, status EM_DIAGNOSTICO e registros operacionais ativos.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}

    # 0. Cadastramos o usuário operador no banco para satisfazer a FK de auditoria dos logs (os_status_logs)
    payload_usuario = {
        "nome": "Recepcionista Teste",
        "email": "recepcao.teste@oficina.com",
        "senha": "senhaSegura123",
        "role": "RECEPCIONISTA",
    }
    # (Opcional: se a rota de cadastro for pública ou se você usar um token de admin/master para criá-lo)
    await async_client.post("/usuarios", json=payload_usuario, headers=headers)

    # 1. Cadastramos um cliente de teste com CPF matematicamente válido
    payload_cliente = {
        "nome": "João das Ordens",
        "email": "joao.os@oficina.com",
        "telefone": "11977778888",
        "cpf_cnpj": "32105222862",
        "tipo_pessoa": "FISICA",
    }
    res_cliente = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers
    )
    assert res_cliente.status_code == status.HTTP_201_CREATED
    cliente_id = res_cliente.json()["id"]

    # 2. Cadastramos um veículo para o cliente
    payload_veiculo = {
        "placa": "XYZ-9876",
        "marca": "Chevrolet",
        "modelo": "Onix",
        "ano": 2022,
        "cliente_id": cliente_id,
    }
    res_veiculo = await async_client.post(
        "/veiculos", json=payload_veiculo, headers=headers
    )
    assert res_veiculo.status_code == status.HTTP_201_CREATED
    veiculo_id = res_veiculo.json()["id"]

    # 3. Solicitamos a abertura da OS sem serviços catalogados (demanda diagnóstico mecânico)
    payload_os = {
        "cliente_id": cliente_id,
        "veiculo_id": veiculo_id,
        "servicos": [],
        "pecas": [],
    }

    response = await async_client.post(
        "/ordens-servico", json=payload_os, headers=headers
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert "id" in body
    assert body["cliente_id"] == cliente_id
    assert body["veiculo_id"] == veiculo_id
    # Sem serviços expressos, a OS obrigatoriamente cai na esteira de Diagnóstico
    assert body["status"] == "EM_DIAGNOSTICO"
    assert body["visualizacao_hash"] is not None


@pytest.mark.asyncio
async def test_gerente_deve_conseguir_abrir_os(
    async_client: AsyncClient, token_gerente: str
):
    """
    Cenário: Gerente tenta abrir uma OS para triagem de pátio.
    Resultado esperado: 201 Created (Gerente herda permissões totais de negócio).
    """
    headers = {"Authorization": f"Bearer {token_gerente}"}

    # Cadastra o cliente e veículo
    payload_cliente = {
        "nome": "Marcos Gerência",
        "email": "marcos.gerencia@oficina.com",
        "telefone": "11955556666",
        "cpf_cnpj": "96292365085",  # 🌟 CPF Matemático Válido para passar no Value Object (CpfCnpj)
        "tipo_pessoa": "FISICA",
    }
    res_cliente = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers
    )
    assert res_cliente.status_code == status.HTTP_201_CREATED
    cliente_id = res_cliente.json()["id"]

    payload_veiculo = {
        "placa": "MGR-4321",
        "marca": "Toyota",
        "modelo": "Corolla",
        "ano": 2021,
        "cliente_id": cliente_id,
    }
    res_veiculo = await async_client.post(
        "/veiculos", json=payload_veiculo, headers=headers
    )
    assert res_veiculo.status_code == status.HTTP_201_CREATED
    veiculo_id = res_veiculo.json()["id"]

    payload_os = {
        "cliente_id": cliente_id,
        "veiculo_id": veiculo_id,
        "servicos": [],
        "pecas": [],
    }

    response = await async_client.post(
        "/ordens-servico", json=payload_os, headers=headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["status"] == "EM_DIAGNOSTICO"


@pytest.mark.asyncio
async def test_mecanico_nao_deve_conseguir_abrir_os(
    async_client: AsyncClient, token_mecanico: str
):
    """
    Cenário: Mecânico tenta abrir uma OS (violação de papéis e barreira de segurança RBAC).
    Resultado esperado: 403 Forbidden.
    """
    headers = {"Authorization": f"Bearer {token_mecanico}"}
    payload_os = {
        "cliente_id": str(uuid7()),
        "veiculo_id": str(uuid7()),
        "servicos": [],
    }

    response = await async_client.post(
        "/ordens-servico", json=payload_os, headers=headers
    )

    # 🛡️ O RBAC na borda do FastAPI deve rejeitar o acesso!
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_estoquista_nao_deve_conseguir_abrir_os(
    async_client: AsyncClient, token_estoquista: str
):
    """
    Cenário: Estoquista tenta criar uma OS (violação de papel).
    Resultado esperado: 403 Forbidden.
    """
    headers = {"Authorization": f"Bearer {token_estoquista}"}
    payload_os = {
        "cliente_id": str(uuid7()),
        "veiculo_id": str(uuid7()),
        "servicos": [],
    }

    response = await async_client.post(
        "/ordens-servico", json=payload_os, headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_usuario_nao_autenticado_deve_receber_401(async_client: AsyncClient):
    """
    Cenário: Chamada de abertura de OS sem apresentar cabeçalho de autenticação Bearer.
    Resultado esperado: 401 Unauthorized.
    """
    payload_os = {
        "cliente_id": str(uuid7()),
        "veiculo_id": str(uuid7()),
        "servicos": [],
    }

    response = await async_client.post("/ordens-servico", json=payload_os)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_falha_cliente_nao_encontrado_ao_abrir_os(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Tentativa de abrir OS com ID de cliente inexistente.
    Resultado esperado: 404 Not Found.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    payload_os = {
        "cliente_id": str(uuid7()),
        "veiculo_id": str(uuid7()),
        "servicos": [],
        "pecas": [],
    }
    response = await async_client.post(
        "/ordens-servico", json=payload_os, headers=headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_falha_veiculo_nao_encontrado_ao_abrir_os(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Tentativa de abrir OS com cliente válido, mas veículo inexistente.
    Resultado esperado: 404 Not Found.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}

    uid = str(uuid7())[:6]
    payload_cliente = {
        "nome": "Cliente Sem Carro",
        "email": f"sem.carro.{uid}@oficina.com",
        "telefone": "11944443333",
        "cpf_cnpj": "52889394034",  # CPF Válido
        "tipo_pessoa": "FISICA",
    }
    res_cli = await async_client.post("/clientes", json=payload_cliente, headers=headers)
    assert res_cli.status_code == status.HTTP_201_CREATED
    cliente_id = res_cli.json()["id"]

    payload_os = {
        "cliente_id": cliente_id,
        "veiculo_id": str(uuid7()),
        "servicos": [],
        "pecas": [],
    }
    response = await async_client.post(
        "/ordens-servico", json=payload_os, headers=headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_falha_servico_inexistente_no_catalogo(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Tentativa de abrir OS informando um serviço que não existe no catálogo.
    Resultado esperado: 400 Bad Request.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}

    uid = str(uuid7())[:6]
    cpf_valido = CPF().generate()  # 🌟 Perfeito! Usando a biblioteca documentada
    placa_valida = gerar_placa_valida_para_teste()  # 🌟 Placa Mercosul válida gerada dinamicamente
    
    # 1. Cadastra o cliente com CPF válido da biblioteca
    payload_cliente = {
        "nome": "Cliente Catálogo",
        "email": f"catalogo.{uid}@oficina.com",
        "telefone": "11933332222",
        "cpf_cnpj": cpf_valido,
        "tipo_pessoa": "FISICA",
    }
    res_cli = await async_client.post("/clientes", json=payload_cliente, headers=headers)
    assert res_cli.status_code == status.HTTP_201_CREATED
    cliente_id = res_cli.json()["id"]

    # 2. Cadastra o veículo com placa Mercosul válida e sem colisão de banco
    payload_vei = {
        "placa": placa_valida,  
        "marca": "Fiat",
        "modelo": "Palio",
        "ano": 2010,
        "cliente_id": cliente_id,
    }
    res_vei = await async_client.post("/veiculos", json=payload_vei, headers=headers)
    assert res_vei.status_code == status.HTTP_201_CREATED
    veiculo_id = res_vei.json()["id"]

    # 3. Tenta abrir a OS enviando um ID de serviço inexistente
    payload_os = {
        "cliente_id": cliente_id,
        "veiculo_id": veiculo_id,
        "servicos_solicitados": [{"servico_id": str(uuid7())}],  
        "pecas_solicitadas": [],                                 
    }

    response = await async_client.post(
        "/ordens-servico", json=payload_os, headers=headers
    )
    
    # 4. Agora a barreira de validação cadastral passa lisa e bate no erro de negócio do catálogo
    assert response.status_code == status.HTTP_400_BAD_REQUEST