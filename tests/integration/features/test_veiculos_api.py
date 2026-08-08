import pytest
from fastapi import status
from httpx import AsyncClient


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
        "placa": "abc1d23",  # Letras minúsculas sem hífen
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
    assert body["placa"] == "ABC1D23"


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
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


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
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
