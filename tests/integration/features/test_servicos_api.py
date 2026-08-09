# tests/integration/features/test_cadastrar_servico.py
import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_recepcionista_deve_cadastrar_servico_com_sucesso(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Recepcionista tenta cadastrar um novo serviço válido de mão de obra.
    Resultado esperado: 201 Created, serviço salvo no banco com ID (UUIDv7) e ativo por padrão.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    payload = {
        "nome": "Alinhamento e Balanceamento 3D",
        "descricao": "Alinhamento completo computadorizado de eixos e balanceamento de rodas",
        "preco_mao_de_obra": 120.00,
        "duracao_estimada_minutos": 45
    }

    response = await async_client.post("/servicos", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    
    body = response.json()
    assert "id" in body
    assert body["nome"] == "Alinhamento e Balanceamento 3D"
    assert body["descricao"] == "Alinhamento completo computadorizado de eixos e balanceamento de rodas"
    assert body["preco_mao_de_obra"] == "120.00"
    assert body["duracao_estimada_minutos"] == 45
    assert body["ativo"] is True


@pytest.mark.asyncio
async def test_gerente_deve_cadastrar_servico_com_sucesso(
    async_client: AsyncClient, token_gerente: str
):
    """
    Cenário: Gerente tenta cadastrar um novo serviço de diagnóstico pesado.
    Resultado esperado: 201 Created com sucesso.
    """
    headers = {"Authorization": f"Bearer {token_gerente}"}
    payload = {
        "nome": "Diagnóstico do Motor por Varredura OBD2",
        "descricao": "Leitura completa de sensores de injeção e eletrônica do veículo",
        "preco_mao_de_obra": 150.00,
        "duracao_estimada_minutos": 30
    }

    response = await async_client.post("/servicos", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    
    body = response.json()
    assert body["nome"] == "Diagnóstico do Motor por Varredura OBD2"


@pytest.mark.asyncio
async def test_cadastrar_servico_com_nome_duplicado_deve_retornar_409(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Recepcionista tenta cadastrar um serviço com nome idêntico a um já catalogado.
    Resultado esperado: 409 Conflict devido à regra de unicidade cadastral de serviço.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    payload = {
        "nome": "Troca de Óleo e Filtro Castrol",
        "descricao": "Troca padrão de óleo lubrificante sintético 5W30 e filtro correspondente",
        "preco_mao_de_obra": 80.00,
        "duracao_estimada_minutos": 30
    }

    # Primeiro cadastro
    res_1 = await async_client.post("/servicos", json=payload, headers=headers)
    assert res_1.status_code == status.HTTP_201_CREATED

    # Segunda tentativa (duplicada)
    res_2 = await async_client.post("/servicos", json=payload, headers=headers)
    assert res_2.status_code == status.HTTP_409_CONFLICT
    assert res_2.json()["detail"] == "Já existe um serviço cadastrado com este nome."


@pytest.mark.asyncio
async def test_cadastrar_servico_com_valores_invalidos_deve_retornar_422(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Recepcionista tenta cadastrar um serviço com preço zerado ou negativo.
    Resultado esperado: 422 Unprocessable Entity (bloqueado por validação do Pydantic).
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    payload = {
        "nome": "Lavagem Expressa Simples",
        "preco_mao_de_obra": 0.00,  # Preço inválido, deve ser gt=0!
        "duracao_estimada_minutos": 20
    }

    response = await async_client.post("/servicos", json=payload, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_mecanico_nao_deve_ter_permissao_de_cadastrar_servico(
    async_client: AsyncClient, token_mecanico: str
):
    """
    Cenário: Mecânico tenta registrar um novo serviço no catálogo da oficina.
    Resultado esperado: 403 Forbidden (RBAC bloqueando papéis não gerenciais).
    """
    headers = {"Authorization": f"Bearer {token_mecanico}"}
    payload = {
        "nome": "Retífica Completa de Cabeçote",
        "preco_mao_de_obra": 1500.00,
        "duracao_estimada_minutos": 480
    }

    response = await async_client.post("/servicos", json=payload, headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_estoquista_nao_deve_ter_permissao_de_cadastrar_servico(
    async_client: AsyncClient, token_estoquista: str
):
    """
    Cenário: Estoquista tenta registrar um novo serviço no catálogo da oficina.
    Resultado esperado: 403 Forbidden.
    """
    headers = {"Authorization": f"Bearer {token_estoquista}"}
    payload = {
        "nome": "Pintura de Para-choque Dianteiro",
        "preco_mao_de_obra": 400.00,
        "duracao_estimada_minutos": 120
    }

    response = await async_client.post("/servicos", json=payload, headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
