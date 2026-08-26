import pytest
from fastapi import status
from httpx import AsyncClient
from uuid import uuid7, UUID
from sqlalchemy import select
from app.features.clientes.models import Cliente
from app.features.usuarios.models import Usuario
import base64
import json


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

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


from validate_docbr import CPF, CNPJ


async def garantir_usuario_existe_no_banco(token: str, role: str, db) -> str:
    """Decodifica o payload do JWT, obtém o sub (UUID) e insere fisicamente na tabela usuarios se não existir."""
    from app.features.usuarios.models import Usuario
    from sqlalchemy import select

    token_parts = token.split(".")
    payload_decoded = base64.b64decode(token_parts[1] + "==").decode("utf-8")
    payload_json = json.loads(payload_decoded)
    user_id = payload_json["sub"]

    res = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user_db = res.scalar_one_or_none()
    if not user_db:
        new_user = Usuario(
            id=UUID(user_id),
            nome=f"Usuario Teste {role.capitalize()}",
            email=f"{role.lower()}.teste@oficina.com",
            role=role,
            ativo=True,
        )
        db.add(new_user)
        await db.commit()
    return user_id


@pytest.mark.asyncio
async def test_editar_cliente_com_sucesso(
    async_client: AsyncClient, token_recepcionista: str, db
):
    """
    Cenário: Recepcionista atualiza nome, email e telefone de um cliente existente de forma bem-sucedida.
    Resultado esperado: 200 OK com os dados atualizados e formatados de forma rica.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    await garantir_usuario_existe_no_banco(token_recepcionista, "RECEPCIONISTA", db)

    uid = str(uuid7())[:6]
    cpf_doc = CPF().generate()

    # 1. Cria o cliente original
    payload_cliente = {
        "nome": f"Cliente Teste Original {uid}",
        "email": f"cliente.original.{uid}@gmail.com",
        "telefone": "11988887777",
        "cpf_cnpj": cpf_doc,
        "tipo_pessoa": "FISICA",
    }
    res_cliente = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers
    )
    assert res_cliente.status_code == status.HTTP_201_CREATED
    cliente_id = res_cliente.json()["id"]

    # 2. Executa a edição de dados parciais
    payload_edicao = {
        "nome": f"Cliente Teste Editado {uid}",
        "email": f"cliente.editado.{uid}@gmail.com",
        "telefone": "11977776666",
    }
    response = await async_client.put(
        f"/clientes/{cliente_id}", json=payload_edicao, headers=headers
    )

    # 3. Asserções
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == cliente_id
    assert body["nome"] == f"Cliente Teste Editado {uid}"
    assert body["email"] == f"cliente.editado.{uid}@gmail.com"
    assert body["telefone"] == "11977776666"  # Formatado pelo VO
    assert (
        body["cpf_cnpj"] == f"{cpf_doc[:3]}.{cpf_doc[3:6]}.{cpf_doc[6:9]}-{cpf_doc[9:]}"
    )  # Formatado pelo VO
    assert body["tipo_pessoa"] == "FISICA"


@pytest.mark.asyncio
async def test_editar_cliente_enviando_valores_nulos_deve_preservar_originais(
    async_client: AsyncClient, token_recepcionista: str, db
):
    """
    Cenário: Tenta editar um cliente passando campos opcionais como nulos ou omitidos no payload.
             Garante que o Handler e o Schema lidem corretamente com atualizações parciais.
    Resultado esperado: 200 OK com os valores omitidos ignorados, preservando os dados originais.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    await garantir_usuario_existe_no_banco(token_recepcionista, "RECEPCIONISTA", db)

    uid = str(uuid7())[:6]
    cpf_doc = CPF().generate()

    # 1. Cria o cliente original
    payload_cliente = {
        "nome": f"Cliente Carla {uid}",
        "email": f"carla.preservar.{uid}@gmail.com",
        "telefone": "11955554444",
        "cpf_cnpj": cpf_doc,
        "tipo_pessoa": "FISICA",
    }
    res_cliente = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers
    )
    assert res_cliente.status_code == status.HTTP_201_CREATED
    cliente_id = res_cliente.json()["id"]

    # 2. Executa a edição omitindo as chaves não alteradas.
    payload_edicao = {"nome": f"Cliente Carla Editada {uid}"}
    response = await async_client.put(
        f"/clientes/{cliente_id}", json=payload_edicao, headers=headers
    )

    # 3. Asserções (valores omitidos preservam os dados originais)
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["nome"] == f"Cliente Carla Editada {uid}"
    assert body["email"] == f"carla.preservar.{uid}@gmail.com"
    assert body["telefone"] == "11955554444"
    assert body["tipo_pessoa"] == "FISICA"


@pytest.mark.asyncio
async def test_editar_cliente_mesmo_email_e_cpf_nao_deve_gerar_conflito(
    async_client: AsyncClient, token_recepcionista: str, db
):
    """
    Cenário: Edita um cliente enviando o mesmo e-mail e CPF/CNPJ que ele já possui (com ou sem formatação de caixa).
             Isso exercita a ramificação lógica que impede falsos conflitos de unicidade no Handler.
    Resultado esperado: 200 OK.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    await garantir_usuario_existe_no_banco(token_recepcionista, "RECEPCIONISTA", db)

    uid = str(uuid7())[:6]
    cpf_doc = CPF().generate()
    email_original = f"CLAN.{uid}@OFICINA.com"

    # 1. Cria o cliente
    payload_cliente = {
        "nome": f"Cliente Mesmos Dados {uid}",
        "email": email_original,
        "telefone": "11944443333",
        "cpf_cnpj": cpf_doc,
        "tipo_pessoa": "FISICA",
    }
    res_cliente = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers
    )
    assert res_cliente.status_code == status.HTTP_201_CREATED
    cliente_id = res_cliente.json()["id"]

    # 2. Executa a edição enviando o mesmo email e CPF de formas variantes de caixa/máscaras
    payload_edicao = {
        "email": f"  clan.{uid}@oficina.com  ",  # Mesmo e-mail com espaços e caixa baixa
        "cpf_cnpj": f"{cpf_doc[:3]}.{cpf_doc[3:6]}.{cpf_doc[6:9]}-{cpf_doc[9:]}",  # Mesmo CPF com pontos e traços
        "nome": f"Cliente Mesmos Dados Atualizado {uid}",
    }
    response = await async_client.put(
        f"/clientes/{cliente_id}", json=payload_edicao, headers=headers
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["email"] == f"clan.{uid}@oficina.com"  # Padronizado em caixa baixa
    assert body["nome"] == f"Cliente Mesmos Dados Atualizado {uid}"


@pytest.mark.asyncio
async def test_editar_cliente_inexistente_deve_retornar_404(
    async_client: AsyncClient, token_recepcionista: str, db
):
    """
    Cenário: Tenta editar um cliente que não está cadastrado no sistema.
    Resultado esperado: 404 Not Found.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    await garantir_usuario_existe_no_banco(token_recepcionista, "RECEPCIONISTA", db)

    payload_edicao = {"nome": "Cliente Fantasma"}
    id_fake = str(uuid7())
    response = await async_client.put(
        f"/clientes/{id_fake}", json=payload_edicao, headers=headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Cliente não encontrado."


@pytest.mark.asyncio
async def test_editar_cliente_duplicidade_email_deve_retornar_409(
    async_client: AsyncClient, token_recepcionista: str, db
):
    """
    Cenário: Tenta editar o e-mail do Cliente B para o mesmo e-mail já cadastrado para o Cliente A.
    Resultado esperado: 409 Conflict.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    await garantir_usuario_existe_no_banco(token_recepcionista, "RECEPCIONISTA", db)

    uid = str(uuid7())[:6]

    # 1. Cadastra Cliente A
    payload_a = {
        "nome": f"Cliente Letra A {uid}",
        "email": f"letra.a.{uid}@oficina.com",
        "telefone": "11988881111",
        "cpf_cnpj": CPF().generate(),
        "tipo_pessoa": "FISICA",
    }
    await async_client.post("/clientes", json=payload_a, headers=headers)

    # 2. Cadastra Cliente B
    payload_b = {
        "nome": f"Cliente Letra B {uid}",
        "email": f"letra.b.{uid}@oficina.com",
        "telefone": "11988882222",
        "cpf_cnpj": CPF().generate(),
        "tipo_pessoa": "FISICA",
    }
    res_b = await async_client.post("/clientes", json=payload_b, headers=headers)
    cliente_b_id = res_b.json()["id"]

    # 3. Tenta editar o Cliente B para usar o e-mail do Cliente A
    payload_edicao = {"email": f"letra.a.{uid}@oficina.com"}
    response = await async_client.put(
        f"/clientes/{cliente_b_id}", json=payload_edicao, headers=headers
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert (
        response.json()["detail"]
        == "O e-mail informado já está em uso por outro cliente."
    )


@pytest.mark.asyncio
async def test_editar_cliente_duplicidade_documento_deve_retornar_409(
    async_client: AsyncClient, token_recepcionista: str, db
):
    """
    Cenário: Tenta editar o CPF/CNPJ do Cliente B para o mesmo documento já cadastrado para o Cliente A.
    Resultado esperado: 409 Conflict.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    await garantir_usuario_existe_no_banco(token_recepcionista, "RECEPCIONISTA", db)

    uid = str(uuid7())[:6]
    cpf_a = CPF().generate()
    cpf_b = CPF().generate()

    # 1. Cadastra Cliente A
    payload_a = {
        "nome": f"Cliente Doc A {uid}",
        "email": f"doc.a.{uid}@oficina.com",
        "telefone": "11977771111",
        "cpf_cnpj": cpf_a,
        "tipo_pessoa": "FISICA",
    }
    await async_client.post("/clientes", json=payload_a, headers=headers)

    # 2. Cadastra Cliente B
    payload_b = {
        "nome": f"Cliente Doc B {uid}",
        "email": f"doc.b.{uid}@oficina.com",
        "telefone": "11977772222",
        "cpf_cnpj": cpf_b,
        "tipo_pessoa": "FISICA",
    }
    res_b = await async_client.post("/clientes", json=payload_b, headers=headers)
    cliente_b_id = res_b.json()["id"]

    # 3. Tenta editar o Cliente B para usar o CPF do Cliente A
    payload_edicao = {"cpf_cnpj": cpf_a}
    response = await async_client.put(
        f"/clientes/{cliente_b_id}", json=payload_edicao, headers=headers
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert (
        response.json()["detail"]
        == "Já existe um cliente cadastrado com o documento informado."
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "campo,valor_invalido",
    [
        ("email", "email_invalido_sem_arroba"),
        ("telefone", "1234567"),  # Telefone curto demais
        ("cpf_cnpj", "11111111111"),  # CPF matematicamente inválido
        ("nome", "Jo"),  # Nome curto demais
    ],
)
async def test_editar_cliente_schemas_validacoes_devem_retornar_422(
    async_client: AsyncClient,
    token_recepcionista: str,
    db,
    campo: str,
    valor_invalido: str,
):
    """
    Cenário: Tenta editar um cliente passando dados sintáticos inválidos para validar a barreira dos Schemas.
    Resultado esperado: 422 Unprocessable Entity.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    await garantir_usuario_existe_no_banco(token_recepcionista, "RECEPCIONISTA", db)

    payload_edicao = {campo: valor_invalido}
    response = await async_client.put(
        f"/clientes/{uuid7()}", json=payload_edicao, headers=headers
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_mecanico_nao_deve_ter_permissao_de_editar_cliente(
    async_client: AsyncClient, token_mecanico: str, db
):
    """
    Cenário: Mecânico tenta acessar a rota de edição de clientes (violação de RBAC).
    Resultado esperado: 403 Forbidden.
    """
    headers = {"Authorization": f"Bearer {token_mecanico}"}
    await garantir_usuario_existe_no_banco(token_mecanico, "MECANICO", db)

    payload = {"nome": "Tentativa Invasao Mecanico"}
    response = await async_client.put(
        f"/clientes/{uuid7()}", json=payload, headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_estoquista_nao_deve_ter_permissao_de_editar_cliente(
    async_client: AsyncClient, token_estoquista: str, db
):
    """
    Cenário: Estoquista tenta acessar a rota de edição de clientes (violação de RBAC).
    Resultado esperado: 403 Forbidden.
    """
    headers = {"Authorization": f"Bearer {token_estoquista}"}
    await garantir_usuario_existe_no_banco(token_estoquista, "ESTOQUISTA", db)

    payload = {"nome": "Tentativa Invasao Estoquista"}
    response = await async_client.put(
        f"/clientes/{uuid7()}", json=payload, headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_usuario_nao_autenticado_deve_receber_401_ao_editar_cliente(
    async_client: AsyncClient,
):
    """
    Cenário: Chamada para editar cliente sem passar o cabeçalho Authorization JWT.
    Resultado esperado: 401 Unauthorized.
    """
    payload = {"nome": "Sem Token"}
    response = await async_client.put(f"/clientes/{uuid7()}", json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_gerente_deve_excluir_cliente_sem_vinculos_com_sucesso(
    async_client: AsyncClient, token_gerente: str
):
    headers = {"Authorization": f"Bearer {token_gerente}"}
    cpf_valido = CPF().generate()

    # 1. Cadastra cliente de teste com e-mail unico e CPF valido
    payload_cliente = {
        "nome": "Cliente Sem Vinculos",
        "email": f"excluir.cliente.{uuid7().hex[:6]}@mecanicar.com",
        "telefone": "11966665555",
        "cpf_cnpj": cpf_valido,
        "tipo_pessoa": "FISICA",
    }
    res_cli = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers
    )
    assert res_cli.status_code == status.HTTP_201_CREATED
    cliente_id = res_cli.json()["id"]

    # 2. Exclui o cliente cadastrado (Retorna 200 OK com Schema)
    res_del = await async_client.delete(f"/clientes/{cliente_id}", headers=headers)
    assert res_del.status_code == status.HTTP_200_OK

    body = res_del.json()
    assert body["cliente_id"] == cliente_id
    assert body["nome"] == "Cliente Sem Vinculos"
    assert "removido com sucesso" in body["mensagem"]

    # 3. Garante que nao e possivel encontrar o cliente mais
    res_get = await async_client.get(f"/clientes/{cliente_id}", headers=headers)
    assert res_get.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_deve_bloquear_exclusao_de_cliente_com_veiculo_vinculado(
    async_client: AsyncClient, token_gerente: str
):
    headers = {"Authorization": f"Bearer {token_gerente}"}
    cpf_valido = CPF().generate()

    # 1. Cadastra cliente de teste com e-mail unico e CPF valido
    payload_cliente = {
        "nome": "Cliente Proprietario",
        "email": f"cliente.proprietario.{uuid7().hex[:6]}@mecanicar.com",
        "telefone": "11955554444",
        "cpf_cnpj": cpf_valido,
        "tipo_pessoa": "FISICA",
    }
    res_cli = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers
    )
    assert res_cli.status_code == status.HTTP_201_CREATED
    cliente_id = res_cli.json()["id"]

    # 2. Cadastra veiculo para o cliente
    payload_veiculo = {
        "placa": "EXC1D24",
        "marca": "Chevrolet",
        "modelo": "Cruze",
        "ano": 2020,
        "cliente_id": cliente_id,
    }
    await async_client.post("/veiculos", json=payload_veiculo, headers=headers)

    # 3. Tenta excluir o cliente que agora possui vinculo fisico
    res_del = await async_client.delete(f"/clientes/{cliente_id}", headers=headers)
    assert res_del.status_code == status.HTTP_400_BAD_REQUEST
    assert "possui veiculos ou ordens de servico vinculadas" in res_del.json()["detail"]


@pytest.mark.asyncio
async def test_mecanico_nao_deve_excluir_cliente(
    async_client: AsyncClient, token_mecanico: str
):
    headers = {"Authorization": f"Bearer {token_mecanico}"}
    cliente_id = str(uuid7())

    res_del = await async_client.delete(f"/clientes/{cliente_id}", headers=headers)
    assert res_del.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_excluir_cliente_inexistente_deve_retornar_404(
    async_client: AsyncClient, token_gerente: str
):
    headers = {"Authorization": f"Bearer {token_gerente}"}
    id_inexistente = str(uuid7())

    res_del = await async_client.delete(f"/clientes/{id_inexistente}", headers=headers)
    assert res_del.status_code == status.HTTP_404_NOT_FOUND
