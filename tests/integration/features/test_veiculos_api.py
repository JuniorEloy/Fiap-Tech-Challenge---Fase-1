import pytest
from fastapi import status
from httpx import AsyncClient
from uuid import uuid7
from app.shared.utils.clock import DateTimeProvider
from validate_docbr import CPF
import random
import string

clock = DateTimeProvider()


def gerar_placa_valida_para_teste() -> str:
    """Gera uma placa Mercosul válida e aleatória (formato AAA9A99) para evitar colisões cadastrais."""
    letras_aleatorias_1 = "".join(random.choices(string.ascii_uppercase, k=3))
    numero_1 = str(random.randint(0, 9))
    letra_aleatoria_2 = random.choice(string.ascii_uppercase)
    numeros_finais = "".join(random.choices(string.digits, k=2))
    return f"{letras_aleatorias_1}{numero_1}{letra_aleatoria_2}{numeros_finais}"


@pytest.mark.asyncio
async def test_cadastrar_veiculo_tradicional_com_sucesso(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Recepcionista tenta cadastrar um veículo com placa tradicional válida.
    Resultado esperado: 201 Created, placa higienizada e formatada (ABC-1234) pelo VO.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}

    # 1. Cadastramos um cliente de teste primeiro para obter um cliente_id válido
    payload_cliente = {
        "nome": "Carla Silva Veiculos",
        "email": "carla.veiculos@oficina.com",
        "telefone": "11988887777",
        "cpf_cnpj": "52998224725",  # CPF Válido
        "tipo_pessoa": "FISICA",
    }
    res_cliente = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers
    )
    assert res_cliente.status_code == status.HTTP_201_CREATED
    cliente_id = res_cliente.json()["id"]

    # 2. Cadastramos o veículo com placa no formato tradicional antigo (em minúsculas e com hífen)
    payload_veiculo = {
        "placa": "abc-1234",  # Deve ser higienizada pelo Value Object da Placa
        "marca": "Ford",
        "modelo": "Ka",
        "ano": 2020,
        "cliente_id": cliente_id,
    }
    response = await async_client.post(
        "/veiculos", json=payload_veiculo, headers=headers
    )

    # 3. Asserções do Veículo cadastrado
    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert "id" in body
    assert body["marca"] == "Ford"
    assert body["modelo"] == "Ka"
    assert body["ano"] == 2020
    assert body["cliente_id"] == cliente_id
    # O Value Object de Placa deve ter higienizado, validado e formatado a saída com hífen
    assert body["placa"] == "ABC-1234"


@pytest.mark.asyncio
async def test_cadastrar_veiculo_mercosul_com_sucesso(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Recepcionista tenta cadastrar um veículo com placa no formato Mercosul válido.
    Resultado esperado: 201 Created, placa higienizada (ABC1D23) e salva.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}

    # 1. Cadastramos outro cliente de teste para evitar conflito de e-mail e documento
    payload_cliente = {
        "nome": "Julio Mercosul",
        "email": "julio.mercosul@oficina.com",
        "telefone": "11977775555",
        "cpf_cnpj": "28604316086",  # CPF Válido
        "tipo_pessoa": "FISICA",
    }
    res_cliente = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers
    )
    assert res_cliente.status_code == status.HTTP_201_CREATED
    cliente_id = res_cliente.json()["id"]

    # 2. Cadastramos o veículo com placa Mercosul (Letras minúsculas e números alternados)
    payload_veiculo = {
        "placa": "mrc1b23",
        "marca": "Chevrolet",
        "modelo": "Onix",
        "ano": 2022,
        "cliente_id": cliente_id,
    }
    response = await async_client.post(
        "/veiculos", json=payload_veiculo, headers=headers
    )

    # 3. Asserções
    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert "id" in body
    assert body["marca"] == "Chevrolet"
    assert body["modelo"] == "Onix"
    # A placa Mercosul não é formatada com hífen, mas deve vir em maiúsculas
    assert body["placa"] == "MRC1B23"


@pytest.mark.asyncio
async def test_cadastrar_veiculo_placa_invalida_deve_retornar_422(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Tentativa de cadastro com placa fora dos padrões tradicionais ou Mercosul.
    Resultado esperado: 422 Unprocessable Entity (Barrado pelo Pydantic + Value Object).
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}

    payload_veiculo = {
        "placa": "placa-bizarra-123",  # Formato inválido
        "marca": "Fiat",
        "modelo": "Uno",
        "ano": 2015,
        "cliente_id": "019fdf6b-b303-77a9-aabd-03cd84ee7ca4",  # Qualquer UUID de exemplo
    }

    response = await async_client.post(
        "/veiculos", json=payload_veiculo, headers=headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_consultar_veiculo_por_placa_com_sucesso(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Recepcionista busca um veículo existente pela placa.
    Resultado esperado: 200 OK com as propriedades do carro formatadas.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}

    # 1. Cria o cliente primeiro para podermos associar ao carro
    payload_cliente = {
        "nome": "Amanda Teste Busca",
        "email": "amanda.busca@oficina.com",
        "telefone": "11966665555",
        "cpf_cnpj": "28604316086",  # CPF Válido
        "tipo_pessoa": "FISICA",
    }
    res_cliente = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers
    )
    assert res_cliente.status_code == status.HTTP_201_CREATED
    cliente_id = res_cliente.json()["id"]

    # 2. Cadastra o veículo correspondente
    payload_veiculo = {
        "placa": "kpg2j45",  # Placa mercosul
        "marca": "Toyota",
        "modelo": "Corolla",
        "ano": 2021,
        "cliente_id": cliente_id,
    }
    res_veiculo = await async_client.post(
        "/veiculos", json=payload_veiculo, headers=headers
    )
    assert res_veiculo.status_code == status.HTTP_201_CREATED

    # 3. Executa a busca direta pela rota GET /veiculos/placa/{placa}
    # Testando com letras maiúsculas/minúsculas e hífens para provar o poder de higienização do VO
    response = await async_client.get("/veiculos/placa/KPG-2J45", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["marca"] == "Toyota"
    assert body["modelo"] == "Corolla"
    assert body["placa"] == "KPG2J45"  # Saída do VO Mercosul sem hífen
    assert body["cliente_id"] == cliente_id


@pytest.mark.asyncio
async def test_consultar_veiculo_inexistente_deve_retornar_404(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Busca por placa de veículo que não está cadastrado na base.
    Resultado esperado: 404 Not Found [4, 5].
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    response = await async_client.get("/veiculos/placa/ZZZ9Z99", headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Veículo não encontrado."


@pytest.mark.asyncio
async def test_consultar_veiculo_com_placa_invalida_deve_retornar_422(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Busca por placa fora dos padrões aceitos AAA-9999 ou Mercosul.
    Resultado esperado: 422 Unprocessable Entity (Value Object impede a execução) [4, 5].
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    response = await async_client.get("/veiculos/placa/placa-com-erro", headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def gerar_placa_valida_para_teste() -> str:
    """Gera uma placa Mercosul válida e aleatória (formato AAA9A99) para evitar colisões cadastrais."""
    letras_aleatorias_1 = "".join(random.choices(string.ascii_uppercase, k=3))
    numero_1 = str(random.randint(0, 9))
    letra_aleatoria_2 = random.choice(string.ascii_uppercase)
    numeros_finais = "".join(random.choices(string.digits, k=2))
    return f"{letras_aleatorias_1}{numero_1}{letra_aleatoria_2}{numeros_finais}"


@pytest.mark.asyncio
async def test_editar_veiculo_com_sucesso(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Recepcionista atualiza marca, modelo e ano de um veículo existente.
    Resultado esperado: 200 OK com os dados atualizados.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    uid = str(uuid7())[:6]

    # 1. Cria um cliente primeiro para associar ao carro de teste
    payload_cliente = {
        "nome": f"Thiago Edicao Veiculos {uid}",
        "email": f"thiago.edicao.{uid}@oficina.com",
        "telefone": "11988887777",
        "cpf_cnpj": CPF().generate(),  # CPF Dinâmico
        "tipo_pessoa": "FISICA",
    }
    res_cliente = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers
    )
    assert res_cliente.status_code == status.HTTP_201_CREATED
    cliente_id = res_cliente.json()["id"]

    # 2. Cria o veículo original
    placa_original = gerar_placa_valida_para_teste()
    payload_veiculo = {
        "placa": placa_original,
        "marca": "Chevrolet",
        "modelo": "Celta",
        "ano": 2012,
        "cliente_id": cliente_id,
    }
    res_veiculo = await async_client.post(
        "/veiculos", json=payload_veiculo, headers=headers
    )
    assert res_veiculo.status_code == status.HTTP_201_CREATED
    veiculo_id = res_veiculo.json()["id"]

    # 3. Executa a edição parcial dos dados do veículo
    payload_edicao = {
        "marca": "Chevrolet Editado",
        "modelo": "Celta Editado",
        "ano": 2013,
    }
    response = await async_client.put(
        f"/veiculos/{veiculo_id}", json=payload_edicao, headers=headers
    )

    # 4. Asserções de alteração bem sucedida
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["marca"] == "Chevrolet Editado"
    assert body["modelo"] == "Celta Editado"
    assert body["ano"] == 2013
    assert (
        body["placa"] == placa_original.upper()
    )  # Mantida a original formatada pelo VO
    assert body["cliente_id"] == cliente_id


@pytest.mark.asyncio
async def test_editar_veiculo_placa_duplicada_deve_retornar_409(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Tenta atualizar a placa de um veículo B para o mesmo valor da placa de um veículo A já existente.
    Resultado esperado: 409 Conflict.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    uid = str(uuid7())[:6]

    # 1. Cria o cliente de teste com CPF único
    payload_cliente = {
        "nome": f"Marcia Duplicidade Placa {uid}",
        "email": f"marcia.duplicidade.{uid}@oficina.com",
        "telefone": "11977776666",
        "cpf_cnpj": CPF().generate(),  # CPF Único
        "tipo_pessoa": "FISICA",
    }
    res_cliente = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers
    )
    assert res_cliente.status_code == status.HTTP_201_CREATED
    cliente_id = res_cliente.json()["id"]

    # Generates two unique plates
    placa_a = gerar_placa_valida_para_teste()
    placa_b = gerar_placa_valida_para_teste()

    # 2. Cria veículo A
    await async_client.post(
        "/veiculos",
        json={
            "placa": placa_a,
            "marca": "VW",
            "modelo": "Gol",
            "ano": 2010,
            "cliente_id": cliente_id,
        },
        headers=headers,
    )

    # 3. Cria veículo B
    res_veiculo_b = await async_client.post(
        "/veiculos",
        json={
            "placa": placa_b,
            "marca": "Fiat",
            "modelo": "Uno",
            "ano": 2011,
            "cliente_id": cliente_id,
        },
        headers=headers,
    )
    veiculo_b_id = res_veiculo_b.json()["id"]

    # 4. Tenta atualizar a placa do veículo B para o valor da placa A (já registrada no veículo A)
    response = await async_client.put(
        f"/veiculos/{veiculo_b_id}", json={"placa": placa_a}, headers=headers
    )

    # 5. Valida bloqueio de duplicidade
    assert response.status_code == status.HTTP_409_CONFLICT
    assert (
        response.json()["detail"] == "Já existe um veículo cadastrado com esta placa."
    )


@pytest.mark.asyncio
async def test_mecanico_nao_deve_ter_permissao_de_editar_veiculo(
    async_client: AsyncClient, token_mecanico: str
):
    """
    Cenário: Mecânico tenta acessar a rota de edição de veículos.
    Resultado esperado: 403 Forbidden (RBAC operando).
    """
    headers = {"Authorization": f"Bearer {token_mecanico}"}
    payload = {"marca": "Ferrari"}

    response = await async_client.put(
        f"/veiculos/{uuid7()}", json=payload, headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_estoquista_nao_deve_ter_permissao_de_editar_veiculo(
    async_client: AsyncClient, token_estoquista: str
):
    """
    Cenário: Estoquista tenta acessar a rota de edição de veículos.
    Resultado esperado: 403 Forbidden (RBAC operando).
    """
    headers = {"Authorization": f"Bearer {token_estoquista}"}
    payload = {"marca": "Lamborghini"}

    response = await async_client.put(
        f"/veiculos/{uuid7()}", json=payload, headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_usuario_nao_autenticado_deve_receber_401_ao_editar_veiculo(
    async_client: AsyncClient,
):
    """
    Cenário: Chamada de edição de veículos sem autenticação.
    Resultado esperado: 401 Unauthorized.
    """
    payload = {"marca": "Porsche"}
    response = await async_client.put(f"/veiculos/{uuid7()}", json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# --- NOVOS TESTES ADICIONADOS PARA SUBIR A COBERTURA DO SCHEMA PARA >90% ---


@pytest.mark.asyncio
async def test_editar_veiculo_schema_placa_invalida_deve_retornar_422(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Tenta editar um veículo passando uma placa fora dos formatos aceitáveis (Tradicional ou Mercosul).
    Resultado esperado: 422 Unprocessable Entity (Erro de validação do Pydantic).
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}

    # Executa a chamada com placa inválida
    payload_edicao = {"placa": "placa-invalida-longa"}
    response = await async_client.put(
        f"/veiculos/{uuid7()}", json=payload_edicao, headers=headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_editar_veiculo_schema_ano_invalido_baixo_deve_retornar_422(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Tenta editar o veículo com ano menor que 1900.
    Resultado esperado: 422 Unprocessable Entity.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}

    payload_edicao = {"ano": 1899}
    response = await async_client.put(
        f"/veiculos/{uuid7()}", json=payload_edicao, headers=headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_editar_veiculo_schema_ano_invalido_alto_deve_retornar_422(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Tenta editar o veículo com ano superior a ano_atual + 1.
    Resultado esperado: 422 Unprocessable Entity.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    ano_limite = clock.agora().year + 2

    payload_edicao = {"ano": ano_limite}
    response = await async_client.put(
        f"/veiculos/{uuid7()}", json=payload_edicao, headers=headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_editar_veiculo_schema_valores_nulos_deve_funcionar_e_preservar_originais(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Tenta editar o veículo passando valores nulos (opcionais) no payload para validar se o Pydantic
             e o Handler tratam os campos opcionais sem falhar e sem alterar os valores já existentes.
    Resultado esperado: 200 OK mantendo os valores originais intactos.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    uid = str(uuid7())[:6]

    # 1. Cria o cliente e o veículo
    payload_cliente = {
        "nome": f"Carla Preservacao {uid}",
        "email": f"carla.preservacao.{uid}@oficina.com",
        "telefone": "11933334444",
        "cpf_cnpj": CPF().generate(),  # CPF Único e dinâmico para evitar colisão!
        "tipo_pessoa": "FISICA",
    }
    res_cliente = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers
    )
    assert res_cliente.status_code == status.HTTP_201_CREATED
    cliente_id = res_cliente.json()["id"]

    placa_original = gerar_placa_valida_para_teste()
    res_veiculo = await async_client.post(
        "/veiculos",
        json={
            "placa": placa_original,
            "marca": "Toyota",
            "modelo": "Corolla",
            "ano": 2020,
            "cliente_id": cliente_id,
        },
        headers=headers,
    )
    assert res_veiculo.status_code == status.HTTP_201_CREATED
    veiculo_id = res_veiculo.json()["id"]

    # 2. Executa a edição enviando um payload em que os campos placa e ano são None (nulos)
    payload_edicao = {
        "placa": None,
        "marca": "Toyota Editado",
        "modelo": "Corolla Editado",
        "ano": None,
        "cliente_id": None,
    }
    response = await async_client.put(
        f"/veiculos/{veiculo_id}", json=payload_edicao, headers=headers
    )
    assert response.status_code == status.HTTP_200_OK

    body = response.json()
    assert body["marca"] == "Toyota Editado"
    assert body["modelo"] == "Corolla Editado"
    # Campos que foram None no payload devem permanecer com os valores originais criados no passo 1
    assert body["placa"] == placa_original.upper()  # Mantém valor original formatado
    assert body["ano"] == 2020
    assert body["cliente_id"] == cliente_id


# --- NOVOS TESTES ADICIONADOS PARA SUBIR A COBERTURA DO HANDLER PARA >90% ---


@pytest.mark.asyncio
async def test_editar_veiculo_inexistente_deve_retornar_404(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Tenta editar um veículo utilizando um ID aleatório que não existe no banco de dados.
    Resultado esperado: 404 Not Found.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    payload_edicao = {"marca": "VW", "modelo": "Fusca", "ano": 1970}
    id_fake = str(uuid7())
    response = await async_client.put(
        f"/veiculos/{id_fake}", json=payload_edicao, headers=headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Veículo não encontrado."


@pytest.mark.asyncio
async def test_editar_veiculo_novo_proprietario_inexistente_deve_retornar_404(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Tenta transferir o veículo para um cliente que não está cadastrado no sistema.
    Resultado esperado: 404 Not Found.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    uid = str(uuid7())[:6]

    # 1. Cria o cliente e o veículo originais
    payload_cliente = {
        "nome": f"Thiago Original {uid}",
        "email": f"thiago.original.{uid}@oficina.com",
        "telefone": "11988887771",
        "cpf_cnpj": CPF().generate(),  # CPF Único
        "tipo_pessoa": "FISICA",
    }
    res_cliente = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers
    )
    assert res_cliente.status_code == status.HTTP_201_CREATED
    cliente_id = res_cliente.json()["id"]

    placa_original = gerar_placa_valida_para_teste()
    res_veiculo = await async_client.post(
        "/veiculos",
        json={
            "placa": placa_original,
            "marca": "Ford",
            "modelo": "Ka",
            "ano": 2015,
            "cliente_id": cliente_id,
        },
        headers=headers,
    )
    assert res_veiculo.status_code == status.HTTP_201_CREATED
    veiculo_id = res_veiculo.json()["id"]

    # 2. Tenta editar o veículo enviando um cliente_id inexistente (fake)
    cliente_id_fake = str(uuid7())
    payload_edicao = {"cliente_id": cliente_id_fake}
    response = await async_client.put(
        f"/veiculos/{veiculo_id}", json=payload_edicao, headers=headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Cliente proprietário não cadastrado."


@pytest.mark.asyncio
async def test_editar_veiculo_transferencia_proprietario_com_sucesso(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Transfere a propriedade de um veículo existente de um Cliente A para um Cliente B já cadastrado.
    Resultado esperado: 200 OK contendo o ID do novo proprietário.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    uid = str(uuid7())[:6]

    # 1. Cadastra Cliente A com CPF Único
    res_cliente_a = await async_client.post(
        "/clientes",
        json={
            "nome": f"Cliente A {uid}",
            "email": f"cliente.a.{uid}@oficina.com",
            "telefone": "11988889999",
            "cpf_cnpj": CPF().generate(),  # CPF Único
            "tipo_pessoa": "FISICA",
        },
        headers=headers,
    )
    assert res_cliente_a.status_code == status.HTTP_201_CREATED
    cliente_a_id = res_cliente_a.json()["id"]

    # 2. Cadastra Cliente B com CPF Único
    res_cliente_b = await async_client.post(
        "/clientes",
        json={
            "nome": f"Cliente B {uid}",
            "email": f"cliente.b.{uid}@oficina.com",
            "telefone": "11988889998",
            "cpf_cnpj": CPF().generate(),  # CPF Único
            "tipo_pessoa": "FISICA",
        },
        headers=headers,
    )
    assert res_cliente_b.status_code == status.HTTP_201_CREATED
    cliente_b_id = res_cliente_b.json()["id"]

    # 3. Cadastra veículo com o proprietário A
    placa_original = gerar_placa_valida_para_teste()
    res_veiculo = await async_client.post(
        "/veiculos",
        json={
            "placa": placa_original,
            "marca": "Fiat",
            "modelo": "Palio",
            "ano": 2010,
            "cliente_id": cliente_a_id,
        },
        headers=headers,
    )
    assert res_veiculo.status_code == status.HTTP_201_CREATED
    veiculo_id = res_veiculo.json()["id"]

    # 4. Transfere a propriedade para o Cliente B
    payload_edicao = {"cliente_id": cliente_b_id}
    response = await async_client.put(
        f"/veiculos/{veiculo_id}", json=payload_edicao, headers=headers
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["cliente_id"] == cliente_b_id


@pytest.mark.asyncio
async def test_editar_veiculo_mesma_placa_nao_deve_gerar_conflito(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Edita um veículo enviando o mesmo valor de placa que ele já possui.
             Isso valida a integridade do Handler que deve ignorar a checagem de duplicidade se a placa não mudou.
    Resultado esperado: 200 OK sem conflito.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    uid = str(uuid7())[:6]

    # 1. Cria o cliente e o veículo
    payload_cliente = {
        "nome": f"Daniel Placa {uid}",
        "email": f"daniel.placa.{uid}@oficina.com",
        "telefone": "11944445555",
        "cpf_cnpj": CPF().generate(),  # CPF Único
        "tipo_pessoa": "FISICA",
    }
    res_cliente = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers
    )
    assert res_cliente.status_code == status.HTTP_201_CREATED
    cliente_id = res_cliente.json()["id"]

    placa_original = gerar_placa_valida_para_teste()
    res_veiculo = await async_client.post(
        "/veiculos",
        json={
            "placa": placa_original,
            "marca": "Hyundai",
            "modelo": "HB20",
            "ano": 2018,
            "cliente_id": cliente_id,
        },
        headers=headers,
    )
    assert res_veiculo.status_code == status.HTTP_201_CREATED
    veiculo_id = res_veiculo.json()["id"]

    # 2. Edita o veículo enviando a mesma placa (mesmo que com formatação diferente)
    payload_edicao = {"placa": placa_original.lower(), "modelo": "HB20 Editado"}
    response = await async_client.put(
        f"/veiculos/{veiculo_id}", json=payload_edicao, headers=headers
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert (
        body["placa"] == placa_original.upper()
    )  # Mantém a mesma placa limpa e formatada
    assert body["modelo"] == "HB20 Editado"


@pytest.mark.asyncio
async def test_gerente_deve_excluir_veiculo_sem_vinculos_com_sucesso(
    async_client: AsyncClient, token_gerente: str
):
    headers = {"Authorization": f"Bearer {token_gerente}"}
    cpf_valido = CPF().generate()

    # 1. Cadastra um cliente de teste unico
    payload_cliente = {
        "nome": "Carla Veiculo",
        "email": f"carla.veiculo.{uuid7().hex[:6]}@mecanicar.com",
        "telefone": "11988887777",
        "cpf_cnpj": cpf_valido,
        "tipo_pessoa": "FISICA",
    }
    res_cli = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers
    )
    assert res_cli.status_code == status.HTTP_201_CREATED
    cliente_id = res_cli.json()["id"]

    # 2. Cadastra o veiculo de teste para este cliente com placa valida mercosul
    placa_teste = gerar_placa_valida_para_teste()
    payload_veiculo = {
        "placa": placa_teste,
        "marca": "Chevrolet",
        "modelo": "Onix",
        "ano": 2022,
        "cliente_id": cliente_id,
    }
    res_vei = await async_client.post(
        "/veiculos", json=payload_veiculo, headers=headers
    )
    assert res_vei.status_code == status.HTTP_201_CREATED
    veiculo_id = res_vei.json()["id"]

    # 3. Executa a exclusao do veiculo cadastrado
    res_del = await async_client.delete(f"/veiculos/{veiculo_id}", headers=headers)
    assert res_del.status_code == status.HTTP_204_NO_CONTENT

    # 4. Garante que nao e possivel encontrar o veiculo mais (consultando pela placa, rota que realmente existe)
    res_get = await async_client.get(f"/veiculos/placa/{placa_teste}", headers=headers)
    assert res_get.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_deve_bloquear_exclusao_de_veiculo_com_ordem_servico_vinculada(
    async_client: AsyncClient, token_gerente: str
):
    headers = {"Authorization": f"Bearer {token_gerente}"}
    cpf_valido = CPF().generate()

    # 1. Cadastra um cliente de teste unico
    payload_cliente = {
        "nome": "Carla Vinculo OS",
        "email": f"carla.vinculo.{uuid7().hex[:6]}@mecanicar.com",
        "telefone": "11988887777",
        "cpf_cnpj": cpf_valido,
        "tipo_pessoa": "FISICA",
    }
    res_cli = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers
    )
    assert res_cli.status_code == status.HTTP_201_CREATED
    cliente_id = res_cli.json()["id"]

    # 2. Cadastra o veiculo de teste com placa valida mercosul
    payload_veiculo = {
        "placa": gerar_placa_valida_para_teste(),
        "marca": "Chevrolet",
        "modelo": "Onix",
        "ano": 2022,
        "cliente_id": cliente_id,
    }
    res_vei = await async_client.post(
        "/veiculos", json=payload_veiculo, headers=headers
    )
    assert res_vei.status_code == status.HTTP_201_CREATED
    veiculo_id = res_vei.json()["id"]

    # 3. Abre uma Ordem de Servico vinculada a este veiculo
    payload_os = {
        "cliente_id": cliente_id,
        "veiculo_id": veiculo_id,
        "servicos": [],
        "pecas": [],
    }
    res_os = await async_client.post(
        "/ordens-servico", json=payload_os, headers=headers
    )
    assert res_os.status_code == status.HTTP_201_CREATED

    # 4. Tenta excluir o veiculo que agora possui vinculo historico/ativo com OS
    res_del = await async_client.delete(f"/veiculos/{veiculo_id}", headers=headers)
    assert res_del.status_code == status.HTTP_400_BAD_REQUEST
    assert "possui ordens de servico vinculadas" in res_del.json()["detail"]


@pytest.mark.asyncio
async def test_mecanico_nao_deve_excluir_veiculo(
    async_client: AsyncClient, token_mecanico: str
):
    headers = {"Authorization": f"Bearer {token_mecanico}"}
    veiculo_id = str(uuid7())

    res_del = await async_client.delete(f"/veiculos/{veiculo_id}", headers=headers)
    assert res_del.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_excluir_veiculo_inexistente_deve_retornar_404(
    async_client: AsyncClient, token_gerente: str
):
    headers = {"Authorization": f"Bearer {token_gerente}"}
    id_inexistente = str(uuid7())

    res_del = await async_client.delete(f"/veiculos/{id_inexistente}", headers=headers)
    assert res_del.status_code == status.HTTP_404_NOT_FOUND
