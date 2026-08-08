import pytest
from fastapi import status
from httpx import AsyncClient
from uuid import uuid7
from sqlalchemy import select
from app.features.clientes.models import Cliente
from app.features.usuarios.models import Usuario


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


@pytest.mark.asyncio
async def test_recepcionista_deve_editar_cliente_com_sucesso_e_sincronizar_usuario(
    async_client: AsyncClient, db, token_recepcionista: str
):
    """
    Cenário: Recepcionista atualiza nome e telefone do cliente.
    Resultado: 200 OK, dados alterados no Cliente e o nome atualizado no Usuário.
    """
    # 1. Cadastramos um cliente de teste primeiro
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    payload_cadastro = {
        "nome": "Marcos Teste",
        "email": "marcos@oficina.com",
        "telefone": "11988887777",
        "cpf_cnpj": "52998224725",  # CPF Válido
        "tipo_pessoa": "FISICA",
    }
    res_cad = await async_client.post(
        "/clientes", json=payload_cadastro, headers=headers
    )
    cliente_id = res_cad.json()["id"]

    # 2. Enviamos a atualização cadastral
    payload_edicao = {"nome": "Marcos Silva Editado", "telefone": "11977776666"}
    response = await async_client.put(
        f"/clientes/{cliente_id}", json=payload_edicao, headers=headers
    )

    # 3. Asserções
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["nome"] == "Marcos Silva Editado"
    assert body["telefone"] == "11977776666"

    # 4. Validação no Banco de dados: o usuário do login também mudou de nome?
    # Buscamos o cliente para pegar o usuario_id
    query_cli = select(Cliente).where(Cliente.id == cliente_id)
    res_cli = await db.execute(query_cli)
    cliente_db = res_cli.scalar_one()

    query_usr = select(Usuario).where(Usuario.id == cliente_db.usuario_id)
    res_usr = await db.execute(query_usr)
    usuario_db = res_usr.scalar_one()

    # O Usuário correspondente deve ter sincronizado o nome perfeitamente!
    assert usuario_db.nome == "Marcos Silva Editado"


@pytest.mark.asyncio
async def test_mecanico_nao_deve_ter_permissao_de_editar_cliente(
    async_client: AsyncClient, token_mecanico: str
):
    """
    Cenário: Mecânico tenta atualizar um cliente.
    Resultado: 403 Forbidden (Bloqueado pelo RBAC).
    """
    headers = {"Authorization": f"Bearer {token_mecanico}"}
    payload = {"nome": "Invasor Malicioso"}

    response = await async_client.put(
        f"/clientes/{uuid7()}", json=payload, headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
