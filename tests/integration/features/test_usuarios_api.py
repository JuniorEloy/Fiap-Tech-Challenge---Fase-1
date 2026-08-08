import pytest
from fastapi import status
from httpx import AsyncClient

# Ajuste a URL caso o seu endpoint seja diferente (ex: "/operadores" ou "/v1/usuarios")
ENDPOINT_USUARIOS = "/usuarios"


@pytest.mark.asyncio
async def test_cadastrar_operador_com_role_gerente_deve_retornar_201(
    async_client: AsyncClient, token_gerente: str
):
    """
    Cenário: Um Gerente tenta cadastrar um novo operador (Mecânico) com dados válidos.
    Resultado esperado: 201 Created.
    * Este teste garante a cobertura do repository, do handler e do salvamento no banco.
    """
    headers = {"Authorization": f"Bearer {token_gerente}"}
    payload = {
        "nome": "Carlos Mecânico",
        "email": "carlos.mecanico@oficina.com",
        "senha": "SenhaSegura123!",
        "role": "MECANICO",
    }

    response = await async_client.post(ENDPOINT_USUARIOS, json=payload, headers=headers)

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert "id" in body
    assert body["nome"] == "Carlos Mecânico"
    assert body["email"] == "carlos.mecanico@oficina.com"
    assert body["role"] == "MECANICO"
    # Garante que a senha não está sendo devolvida no response_model!
    assert "senha" not in body


@pytest.mark.asyncio
async def test_cadastrar_operador_com_role_nao_autorizada_deve_retornar_403(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Uma Recepcionista tenta cadastrar um novo operador (Não permitido pelo RBAC).
    Resultado esperado: 403 Forbidden. A requisição deve ser barrada pelo Depends.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    payload = {
        "nome": "Invasor",
        "email": "invasor@oficina.com",
        "senha": "hacker",
        "role": "GERENTE",
    }

    response = await async_client.post(ENDPOINT_USUARIOS, json=payload, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_cadastrar_operador_com_email_duplicado_deve_retornar_400(
    async_client: AsyncClient, token_gerente: str
):
    headers = {"Authorization": f"Bearer {token_gerente}"}
    payload_primeiro_usuario = {
        "nome": "Usuário Original",
        "email": "email.duplicado@oficina.com",
        "senha": "SenhaForte123!",  # <- Senha válida para o schema
        "role": "RECEPCIONISTA",
    }

    # 1. Cadastra o primeiro usuário
    response_1 = await async_client.post(
        ENDPOINT_USUARIOS, json=payload_primeiro_usuario, headers=headers
    )

    # GARANTIA DE SETUP: Se quebrar aqui, ele te mostra o motivo do 422 no console!
    assert response_1.status_code == status.HTTP_201_CREATED, response_1.json()

    # 2. Tenta cadastrar um segundo usuário com o mesmo e-mail
    payload_segundo_usuario = {
        "nome": "Cópia",
        "email": "email.duplicado@oficina.com",
        "senha": "OutraSenhaForte456!",  # <- Senha válida para o schema
        "role": "MECANICO",
    }

    response_2 = await async_client.post(
        ENDPOINT_USUARIOS, json=payload_segundo_usuario, headers=headers
    )

    # 3. Agora sim, valida o bloqueio da regra de negócio
    assert response_2.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        response_2.json()["detail"]
        == "Já existe um usuário cadastrado com este e-mail."
    )


@pytest.mark.asyncio
async def test_cadastrar_operador_com_payload_invalido_deve_retornar_422(
    async_client: AsyncClient, token_gerente: str
):
    """
    Cenário: Gerente envia uma requisição faltando campos obrigatórios (ex: sem a senha).
    Resultado esperado: 422 Unprocessable Entity (validação do Pydantic).
    """
    headers = {"Authorization": f"Bearer {token_gerente}"}
    payload_incompleto = {
        "nome": "Usuário Sem Senha",
        "email": "sem.senha@oficina.com",
        "role": "MECANICO",
        # O campo 'senha' foi intencionalmente omitido
    }

    response = await async_client.post(
        ENDPOINT_USUARIOS, json=payload_incompleto, headers=headers
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
