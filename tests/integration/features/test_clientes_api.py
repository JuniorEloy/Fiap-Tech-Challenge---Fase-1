import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cadastrar_cliente_com_role_autorizada_deve_retornar_201(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Recepcionista tenta cadastrar um novo cliente válido.
    Resultado esperado: 201 Created com o ID gerado e CPF formatado.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    payload = {
        "nome": "João da Silva",
        "email": "joao.silva@oficina.com",
        "telefone": "11999998888",
        "cpf_cnpj": "28604316086",  # CPF Válido
        "tipo_pessoa": "FISICA",
    }

    response = await async_client.post("/clientes", json=payload, headers=headers)

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert "id" in body
    assert body["nome"] == "João da Silva"
    # O Pydantic deve responder com o CPF perfeitamente formatado
    assert body["cpf_cnpj"] == "286.043.160-86"


@pytest.mark.asyncio
async def test_cadastrar_cliente_com_role_nao_autorizada_deve_retornar_403(
    async_client: AsyncClient, token_mecanico: str
):
    """
    Cenário: Mecânico tenta cadastrar um cliente (Não permitido pelo RBAC).
    Resultado esperado: 403 Forbidden.
    """
    headers = {"Authorization": f"Bearer {token_mecanico}"}
    payload = {
        "nome": "Cliente de Teste",
        "email": "teste@oficina.com",
        "telefone": "11999998888",
        "cpf_cnpj": "12345678901",
        "tipo_pessoa": "FISICA",
    }

    response = await async_client.post("/clientes", json=payload, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_cadastrar_cliente_com_documento_invalido_deve_retornar_422(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Tentativa de cadastro informando um CPF com dígitos verificadores inválidos.
    Resultado esperado: 422 Unprocessable Entity (validação de schema do Pydantic).
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    payload = {
        "nome": "Carlos Inválido",
        "email": "carlos.invalido@oficina.com",
        "telefone": "11999998888",
        "cpf_cnpj": "11111111111",  # CPF Falso/Invalido conceitualmente
        "tipo_pessoa": "FISICA",
    }

    response = await async_client.post("/clientes", json=payload, headers=headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
