# tests/integration/features/test_cadastrar_peca.py
import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_estoquista_deve_cadastrar_peca_com_sucesso(
    async_client: AsyncClient, token_estoquista: str
):
    """
    Cenário: Estoquista tenta cadastrar uma nova peça válida no catálogo.
    Resultado esperado: 201 Created, peça salva no banco com UUIDv7 e precisa_recompra calculado.
    """
    headers = {"Authorization": f"Bearer {token_estoquista}"}
    payload = {
        "nome": "Pastilha de Freio Dianteira Brembo",
        "descricao": "Pastilha cerâmica de alta performance para sedãs",
        "preco_custo": 150.00,
        "preco_venda": 249.90,
        "quantidade_inicial": 20,
        "limite_minimo": 10,
    }

    response = await async_client.post("/estoque", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED

    body = response.json()
    assert "id" in body
    assert body["nome"] == "Pastilha de Freio Dianteira Brembo"
    assert body["quantidade_em_estoque"] == 20
    assert body["preco_custo"] == "150.00"
    assert body["preco_venda"] == "249.90"
    # Como a quantidade_inicial (20) é superior ao limite_minimo (10), não precisa de recompra
    assert body["precisa_recompra"] is False


@pytest.mark.asyncio
async def test_cadastrar_peca_com_preco_venda_inferior_ao_custo_deve_retornar_422(
    async_client: AsyncClient, token_estoquista: str
):
    """
    Cenário: Estoquista tenta catalogar um item com preço de venda abaixo do custo.
    Resultado esperado: 422 Unprocessable Entity (Bloqueado pela regra financeira do DTO).
    """
    headers = {"Authorization": f"Bearer {token_estoquista}"}
    payload = {
        "nome": "Filtro de Ar de Cabine",
        "preco_custo": 80.00,
        "preco_venda": 75.00,  # Menor que o custo, inválido!
        "quantidade_inicial": 5,
    }

    response = await async_client.post("/estoque", json=payload, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "preco_venda" in response.text


@pytest.mark.asyncio
async def test_mecanico_nao_deve_ter_permissao_de_cadastrar_peca(
    async_client: AsyncClient, token_mecanico: str
):
    """
    Cenário: Mecânico tenta cadastrar uma nova peça no catálogo.
    Resultado esperado: 403 Forbidden (RBAC operando com sucesso).
    """
    headers = {"Authorization": f"Bearer {token_mecanico}"}
    payload = {
        "nome": "Filtro de Óleo Fram",
        "preco_custo": 25.00,
        "preco_venda": 45.00,
        "quantidade_inicial": 10,
    }

    response = await async_client.post("/estoque", json=payload, headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
