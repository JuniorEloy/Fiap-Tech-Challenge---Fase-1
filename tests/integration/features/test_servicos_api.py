# tests/integration/features/test_cadastrar_servico.py
import pytest
from fastapi import status
from httpx import AsyncClient
from uuid import uuid7


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
        "nome": "Alinhamento e Balanceamento 4D",
        "descricao": "Alinhamento completo computadorizado de eixos e balanceamento de rodas",
        "preco_mao_de_obra": 120.00,
        "duracao_estimada_minutos": 45,
    }

    response = await async_client.post("/servicos", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED

    body = response.json()
    assert "id" in body
    assert body["nome"] == "Alinhamento e Balanceamento 4D"
    assert (
        body["descricao"]
        == "Alinhamento completo computadorizado de eixos e balanceamento de rodas"
    )
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
        "duracao_estimada_minutos": 30,
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
        "duracao_estimada_minutos": 30,
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
        "duracao_estimada_minutos": 20,
    }

    response = await async_client.post("/servicos", json=payload, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


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
        "duracao_estimada_minutos": 480,
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
        "duracao_estimada_minutos": 120,
    }

    response = await async_client.post("/servicos", json=payload, headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_operador_deve_conseguir_consultar_servico_por_id_com_sucesso(
    async_client: AsyncClient, token_recepcionista: str, token_mecanico: str
):
    """
    Cenário: Recepcionista cadastra um serviço e o Mecânico consulta seus dados por ID.
    Resultado esperado: 200 OK com os dados corretos retornados do catálogo de serviços.
    """
    headers_recep = {"Authorization": f"Bearer {token_recepcionista}"}
    headers_mecanico = {"Authorization": f"Bearer {token_mecanico}"}

    # 1. Cadastramos o serviço de teste
    payload = {
        "nome": "Limpeza do Sistema de Arrefecimento",
        "descricao": "Limpeza química do radiador e troca de aditivo Paraflu",
        "preco_mao_de_obra": 150.00,
        "duracao_estimada_minutos": 60,
    }
    res_cad = await async_client.post("/servicos", json=payload, headers=headers_recep)
    assert res_cad.status_code == status.HTTP_201_CREATED
    servico_id = res_cad.json()["id"]

    # 2. Mecânico realiza a consulta do mesmo serviço
    response = await async_client.get(
        f"/servicos/{servico_id}", headers=headers_mecanico
    )

    # 3. Asserções finais
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == servico_id
    assert body["nome"] == "Limpeza do Sistema de Arrefecimento"
    assert body["preco_mao_de_obra"] == "150.00"
    assert body["duracao_estimada_minutos"] == 60
    assert body["ativo"] is True


@pytest.mark.asyncio
async def test_consultar_servico_inexistente_deve_retornar_404(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Operador tenta consultar um UUID de serviço que não existe no banco.
    Resultado esperado: 404 Not Found.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    random_uuid = str(uuid7())

    response = await async_client.get(f"/servicos/{random_uuid}", headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Serviço não encontrado no catálogo da oficina."


@pytest.mark.asyncio
async def test_estoquista_nao_deve_conseguir_consultar_servico_por_id(
    async_client: AsyncClient, token_estoquista: str
):
    """
    Cenário: Estoquista tenta acessar o endpoint de consulta por ID.
    Resultado esperado: 403 Forbidden pelo controle de RBAC.
    """
    headers = {"Authorization": f"Bearer {token_estoquista}"}
    random_uuid = str(uuid7())

    response = await async_client.get(f"/servicos/{random_uuid}", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_gerente_deve_conseguir_editar_servico_com_sucesso(
    async_client: AsyncClient, token_gerente: str
):
    """
    Cenário: Gerente altera a precificação e a descrição de um serviço existente.
    Resultado esperado: 200 OK com os dados devidamente atualizados e salvos no banco.
    """
    headers = {"Authorization": f"Bearer {token_gerente}"}

    # 1. Cadastra serviço inicial
    payload_cad = {
        "nome": "Descarbonização de Válvulas",
        "descricao": "Limpeza química profunda do coletor de admissão e cabeçote",
        "preco_mao_de_obra": 450.00,
        "duracao_estimada_minutos": 180,
    }
    res_cad = await async_client.post("/servicos", json=payload_cad, headers=headers)
    assert res_cad.status_code == status.HTTP_201_CREATED
    servico_id = res_cad.json()["id"]

    # 2. Solicita a alteração cadastral parcial
    payload_edit = {
        "descricao": "Descarbonização química e física por hidrogênio de válvulas de admissão",
        "preco_mao_de_obra": 499.90,
        "ativo": False,
    }
    response = await async_client.put(
        f"/servicos/{servico_id}", json=payload_edit, headers=headers
    )

    # 3. Asserções finais
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == servico_id
    assert body["nome"] == "Descarbonização de Válvulas"  # Mantido inalterado
    assert (
        body["descricao"]
        == "Descarbonização química e física por hidrogênio de válvulas de admissão"
    )  # Atualizado
    assert body["preco_mao_de_obra"] == "499.90"  # Atualizado
    assert body["duracao_estimada_minutos"] == 180  # Mantido inalterado
    assert body["ativo"] is False  # Atualizado


@pytest.mark.asyncio
async def test_editar_servico_com_nome_conflitante_deve_retornar_409(
    async_client: AsyncClient, token_gerente: str
):
    """
    Cenário: Gerente tenta renomear o Serviço A com o nome idêntico ao Serviço B já existente.
    Resultado esperado: 409 Conflict prevenindo a duplicidade cadastral de chaves.
    """
    headers = {"Authorization": f"Bearer {token_gerente}"}

    # 1. Cadastra o Serviço A
    await async_client.post(
        "/servicos",
        json={
            "nome": "Higienização de Ar Gás",
            "preco_mao_de_obra": 90.00,
            "duracao_estimada_minutos": 30,
        },
        headers=headers,
    )

    # 2. Cadastra o Serviço B
    res_b = await async_client.post(
        "/servicos",
        json={
            "nome": "Instalação de Engate Traseiro",
            "preco_mao_de_obra": 200.00,
            "duracao_estimada_minutos": 60,
        },
        headers=headers,
    )
    servico_b_id = res_b.json()["id"]

    # 3. Tenta renomear o Serviço B para "Higienização de Ar Gás" (Duplicidade!)
    payload_edit = {"nome": "Higienização de Ar Gás"}
    response = await async_client.put(
        f"/servicos/{servico_b_id}", json=payload_edit, headers=headers
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert (
        response.json()["detail"]
        == "Já existe outro serviço cadastrado com este nome no catálogo."
    )


@pytest.mark.asyncio
async def test_mecanico_nao_deve_conseguir_editar_servico(
    async_client: AsyncClient, token_mecanico: str
):
    """
    Cenário: Mecânico tenta reajustar o preço de uma mão de obra do catálogo geral.
    Resultado esperado: 403 Forbidden pelo controle de papéis (RBAC).
    """
    headers = {"Authorization": f"Bearer {token_mecanico}"}
    random_uuid = str(uuid7())

    payload_edit = {"preco_mao_de_obra": 10.00}
    response = await async_client.put(
        f"/servicos/{random_uuid}", json=payload_edit, headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_listar_servicos_deve_retornar_todos_itens_ordenados_alfabeticamente(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Solicitar listagem de serviços sem filtros adicionais.
    Resultado esperado: 200 OK com os itens cadastrados retornados.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}

    # Cadastra dois serviços de referência
    payload_a = {
        "nome": "B_Servico_Beta",
        "preco_mao_de_obra": 100.00,
        "duracao_estimada_minutos": 30,
    }
    payload_b = {
        "nome": "A_Servico_Alfa",
        "preco_mao_de_obra": 200.00,
        "duracao_estimada_minutos": 45,
    }
    await async_client.post("/servicos", json=payload_a, headers=headers)
    await async_client.post("/servicos", json=payload_b, headers=headers)

    response = await async_client.get("/servicos", headers=headers)
    assert response.status_code == status.HTTP_200_OK

    body = response.json()
    assert len(body) >= 2

    # Valida ordenação alfabética (A_Servico_Alfa deve vir antes de B_Servico_Beta)
    nomes = [
        item["nome"]
        for item in body
        if item["nome"] in ["A_Servico_Alfa", "B_Servico_Beta"]
    ]
    assert nomes == ["A_Servico_Alfa", "B_Servico_Beta"]


@pytest.mark.asyncio
async def test_listar_servicos_com_filtro_busca_deve_retornar_apenas_correspondentes(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Filtrar os serviços do catálogo por busca textual.
    Resultado esperado: 200 OK contendo apenas registros cujo nome ou descrição possuam a palavra-chave.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}

    payload_1 = {
        "nome": "Instalação de Insulfilm G5",
        "descricao": "Película de controle solar e privacidade para vidros laterais e traseiro",
        "preco_mao_de_obra": 250.00,
        "duracao_estimada_minutos": 90,
    }
    payload_2 = {
        "nome": "Polimento Técnico Premium",
        "descricao": "Remoção de micro-riscos e vitrificação de pintura automotiva",
        "preco_mao_de_obra": 350.00,
        "duracao_estimada_minutos": 180,
    }
    await async_client.post("/servicos", json=payload_1, headers=headers)
    await async_client.post("/servicos", json=payload_2, headers=headers)

    # Filtrar por "Insulfilm"
    res_busca_1 = await async_client.get("/servicos?busca=Insulfilm", headers=headers)
    assert res_busca_1.status_code == status.HTTP_200_OK
    body_1 = res_busca_1.json()
    assert any(item["nome"] == "Instalação de Insulfilm G5" for item in body_1)
    assert not any(item["nome"] == "Polimento Técnico Premium" for item in body_1)

    # Filtrar por "pintura" (busca textual na descrição - case insensitive)
    res_busca_2 = await async_client.get("/servicos?busca=pintura", headers=headers)
    assert res_busca_2.status_code == status.HTTP_200_OK
    body_2 = res_busca_2.json()
    assert any(item["nome"] == "Polimento Técnico Premium" for item in body_2)
    assert not any(item["nome"] == "Instalação de Insulfilm G5" for item in body_2)


@pytest.mark.asyncio
async def test_estoquista_nao_deve_conseguir_listar_servicos(
    async_client: AsyncClient, token_estoquista: str
):
    """
    Cenário: Papel de Estoquista tenta listar serviços do catálogo da oficina.
    Resultado esperado: 403 Forbidden.
    """
    headers = {"Authorization": f"Bearer {token_estoquista}"}
    response = await async_client.get("/servicos", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
