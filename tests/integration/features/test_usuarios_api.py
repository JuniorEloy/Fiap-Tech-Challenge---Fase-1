import pytest
from fastapi import status
from httpx import AsyncClient
from uuid import uuid7

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


@pytest.mark.asyncio
async def test_gerente_deve_conseguir_editar_operador_com_sucesso(
    async_client: AsyncClient, token_gerente: str
):
    """
    Cenário: O Gerente tenta editar os dados cadastrais e o papel de um operador.
    Resultado esperado: 200 OK com os dados do operador atualizados no banco.
    """
    headers = {"Authorization": f"Bearer {token_gerente}"}

    # 1. Cadastramos um operador de teste usando a rota POST oficial
    payload_cadastro = {
        "nome": "Mecanico Teste",
        "email": "mecanico.teste@oficina.com",
        "senha": "SenhaSecreta123",
        "role": "MECANICO",
    }
    res_cad = await async_client.post(
        "/usuarios", json=payload_cadastro, headers=headers
    )
    assert res_cad.status_code == status.HTTP_201_CREATED
    usuario_id = res_cad.json()["id"]

    # 2. Solicitamos a edição de campos sensíveis (Nome, E-mail, Senha e Status)
    payload_edicao = {
        "nome": "Mecanico Teste Alterado",
        "email": "mecanico.novoemail@oficina.com",
        "senha": "NovaSenhaSuperSegura789",
        "ativo": False,
    }

    response = await async_client.put(
        f"/usuarios/{usuario_id}", json=payload_edicao, headers=headers
    )

    # 3. Asserções finais de sucesso
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["nome"] == "Mecanico Teste Alterado"
    assert body["email"] == "mecanico.novoemail@oficina.com"
    assert (
        body["ativo"] is False
    )  # Conta devidamente desativada temporariamente pelo Gerente


@pytest.mark.asyncio
async def test_gerente_nao_deve_conseguir_editar_com_email_ja_registrado(
    async_client: AsyncClient, token_gerente: str
):
    """
    Cenário: Gerente tenta editar o e-mail de um operador para um endereço que já pertence a outra conta.
    Resultado esperado: 400 Bad Request devido à violação da regra de unicidade cadastral de e-mail.
    """
    headers = {"Authorization": f"Bearer {token_gerente}"}

    # 1. Criamos o Usuário A
    payload_usuario_a = {
        "nome": "Operador Alfa",
        "email": "alfa@oficina.com",
        "senha": "SenhaSecreta123",
        "role": "MECANICO",
    }
    await async_client.post("/usuarios", json=payload_usuario_a, headers=headers)

    # 2. Criamos o Usuário B
    payload_usuario_b = {
        "nome": "Operador Beta",
        "email": "beta@oficina.com",
        "senha": "SenhaSecreta123",
        "role": "ESTOQUISTA",
    }
    res_b = await async_client.post(
        "/usuarios", json=payload_usuario_b, headers=headers
    )
    usuario_b_id = res_b.json()["id"]

    # 3. Tentamos alterar o e-mail do Usuário B para "alfa@oficina.com" (conflito!)
    payload_edicao = {"email": "alfa@oficina.com"}
    response = await async_client.put(
        f"/usuarios/{usuario_b_id}", json=payload_edicao, headers=headers
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        response.json()["detail"] == "Já existe um usuário cadastrado com este e-mail."
    )


@pytest.mark.asyncio
async def test_recepcionista_nao_deve_conseguir_editar_operador(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Um operador sem permissões de gerência (ex: Recepcionista) tenta editar os dados de um usuário.
    Resultado esperado: 403 Forbidden pelo controle de acesso baseado em papéis (RBAC).
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}

    # Tentativa direta em um UUID qualquer
    payload_edicao = {"nome": "Tentativa Invasiva"}

    random_id = str(uuid7())
    response = await async_client.put(
        f"/usuarios/{random_id}", json=payload_edicao, headers=headers
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_gerente_deve_conseguir_consultar_operador_com_sucesso(
    async_client: AsyncClient, token_gerente: str
):
    """
    Cenário: O Gerente tenta consultar os dados detalhados de um operador pelo ID.
    Resultado esperado: 200 OK com os dados do operador cadastrados.
    """
    headers = {"Authorization": f"Bearer {token_gerente}"}

    # 1. Cadastramos um operador de teste usando a rota POST oficial
    payload_cadastro = {
        "nome": "Mecanico Teste Consulta",
        "email": "mecanico.consulta@oficina.com",
        "senha": "SenhaSecreta123",
        "role": "MECANICO",
    }
    res_cad = await async_client.post(
        "/usuarios", json=payload_cadastro, headers=headers
    )
    assert res_cad.status_code == status.HTTP_201_CREATED
    usuario_id = res_cad.json()["id"]

    # 2. Solicitamos a consulta pelo ID
    response = await async_client.get(f"/usuarios/{usuario_id}", headers=headers)

    # 3. Asserções finais de sucesso
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == usuario_id
    assert body["nome"] == "Mecanico Teste Consulta"
    assert body["email"] == "mecanico.consulta@oficina.com"
    assert body["role"] == "MECANICO"
    assert body["ativo"] is True


@pytest.mark.asyncio
async def test_gerente_consultar_usuario_inexistente_deve_retornar_404(
    async_client: AsyncClient, token_gerente: str
):
    """
    Cenário: O Gerente tenta consultar um usuário com ID inexistente no banco.
    Resultado esperado: 404 Not Found.
    """
    headers = {"Authorization": f"Bearer {token_gerente}"}
    random_id = str(uuid7())

    response = await async_client.get(f"/usuarios/{random_id}", headers=headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Usuário não encontrado."


@pytest.mark.asyncio
async def test_recepcionista_nao_deve_conseguir_consultar_operador(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Um operador sem permissões de gerência (ex: Recepcionista) tenta consultar dados de um usuário pelo ID.
    Resultado esperado: 403 Forbidden pelo controle de acesso baseado em papéis (RBAC).
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    random_id = str(uuid7())

    response = await async_client.get(f"/usuarios/{random_id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
