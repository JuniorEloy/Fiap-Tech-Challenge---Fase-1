# tests/integration/features/test_cadastrar_peca.py
import pytest
from fastapi import status
from httpx import AsyncClient
import asyncio
from uuid import uuid7


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
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
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


@pytest.mark.asyncio
async def test_baixar_estoque_com_sucesso(
    async_client: AsyncClient, token_mecanico: str, token_estoquista: str
):
    """
    Cenário: Mecânico solicita a baixa de estoque de uma peça existente.
    Resultado esperado: 200 OK com saldo deduzido e indicador precisa_recompra=False (se saldo >= 15).
    """
    headers_estoquista = {"Authorization": f"Bearer {token_estoquista}"}
    headers_mecanico = {"Authorization": f"Bearer {token_mecanico}"}

    # 1. Cadastra uma peça pelo Estoquista com 50 unidades de saldo inicial
    payload_cadastro = {
        "nome": "Pastilha de Freio Bosch Flex",
        "descricao": "Pastilha dianteira de alta performance",
        "quantidade_inicial": 50,
        "preco_venda": 180.00,
        "preco_custo": 90.00,
        "limite_minimo": 15,
    }
    res_cadastro = await async_client.post(
        "/estoque", json=payload_cadastro, headers=headers_estoquista
    )
    assert res_cadastro.status_code == status.HTTP_201_CREATED
    peca_id = res_cadastro.json()["id"]

    # 2. Mecânico realiza a baixa de 10 unidades
    payload_baixa = {"peca_id": peca_id, "quantidade": 10}
    response = await async_client.post(
        "/estoque/baixas", json=payload_baixa, headers=headers_mecanico
    )

    # 3. Validações finais
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["peca_id"] == peca_id
    assert body["quantidade_retirada"] == 10
    assert body["saldo_restante"] == 40  # 50 - 10
    assert body["precisa_recompra"] is False


@pytest.mark.asyncio
async def test_baixar_estoque_insuficiente_deve_retornar_400(
    async_client: AsyncClient, token_mecanico: str, token_estoquista: str
):
    """
    Cenário: Mecânico tenta baixar uma quantidade superior ao saldo atual disponível.
    Resultado esperado: 400 Bad Request com mensagem descritiva de estoque insuficiente.
    """
    headers_estoquista = {"Authorization": f"Bearer {token_estoquista}"}
    headers_mecanico = {"Authorization": f"Bearer {token_mecanico}"}

    # 1. Cadastra peça com estoque pequeno (ex: 5 unidades)
    payload_cadastro = {
        "nome": "Filtro de Ar Esportivo K&N",
        "descricao": "Filtro inbox lavável",
        "quantidade_inicial": 5,
        "preco_venda": 450.00,
        "preco_custo": 250.00,
        "limite_minimo": 15,
    }
    res_cadastro = await async_client.post(
        "/estoque", json=payload_cadastro, headers=headers_estoquista
    )
    peca_id = res_cadastro.json()["id"]

    # 2. Tenta baixar 8 unidades (excedendo as 5 disponíveis)
    payload_baixa = {"peca_id": peca_id, "quantidade": 8}
    response = await async_client.post(
        "/estoque/baixas", json=payload_baixa, headers=headers_mecanico
    )

    # 3. Validações de erro
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Estoque insuficiente" in response.json()["detail"]


@pytest.mark.asyncio
async def test_baixar_estoque_gatilho_politica_compra_menor_que_15(
    async_client: AsyncClient, token_mecanico: str, token_estoquista: str
):
    """
    Cenário: Baixa de estoque deixa o saldo remanescente abaixo do limite de segurança (15 itens).
    Resultado esperado: Disparo lógico da política indicando precisa_recompra=True.
    """
    headers_estoquista = {"Authorization": f"Bearer {token_estoquista}"}
    headers_mecanico = {"Authorization": f"Bearer {token_mecanico}"}

    # 1. Cadastra peça com estoque inicial de 20 unidades
    payload_cadastro = {
        "nome": "Óleo de Câmbio Motul ATF VI",
        "descricao": "Lubrificante 100% sintético para transmissão automática",
        "quantidade_inicial": 20,
        "preco_venda": 95.00,
        "preco_custo": 50.00,
        "limite_minimo": 15,
    }
    res_cadastro = await async_client.post(
        "/estoque", json=payload_cadastro, headers=headers_estoquista
    )
    peca_id = res_cadastro.json()["id"]

    # 2. Mecânico baixa 8 unidades (saldo cai para 12, que é menor que 15)
    payload_baixa = {"peca_id": peca_id, "quantidade": 8}
    response = await async_client.post(
        "/estoque/baixas", json=payload_baixa, headers=headers_mecanico
    )

    # 3. Valida se a política de disparo de compra foi ativada
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["saldo_restante"] == 12
    assert (
        body["precisa_recompra"] is True
    )  # 👈 Política de domínio ativada com sucesso!


@pytest.mark.asyncio
async def test_baixar_estoque_rbac_bloqueia_recepcionista(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Um operador sem atribuição mecânica (ex: Recepcionista) tenta dar baixa direta de estoque.
    Resultado esperado: 403 Forbidden (RBAC operando com sucesso).
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    payload_baixa = {"peca_id": str(uuid7()), "quantidade": 1}
    response = await async_client.post(
        "/estoque/baixas", json=payload_baixa, headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_estoquista_deve_registrar_entrada_com_sucesso(
    async_client: AsyncClient, token_estoquista: str
):
    """
    Cenário: Estoquista solicita a entrada de estoque para uma peça existente.
    Resultado esperado: 200 OK com saldo acrescido e precisa_recompra reavaliado.
    """
    headers = {"Authorization": f"Bearer {token_estoquista}"}

    # 1. Cadastra uma peça com 5 unidades de saldo inicial (precisa_recompra = True)
    payload_cadastro = {
        "nome": "Filtro de Cabine Tecfil",
        "descricao": "Filtro de ar-condicionado anti-polen",
        "quantidade_inicial": 5,
        "preco_venda": 45.00,
        "preco_custo": 20.00,
        "limite_minimo": 15,
    }
    res_cadastro = await async_client.post(
        "/estoque", json=payload_cadastro, headers=headers
    )
    assert res_cadastro.status_code == status.HTTP_201_CREATED
    peca_id = res_cadastro.json()["id"]
    assert res_cadastro.json()["precisa_recompra"] is True

    # 2. Registra entrada de 20 unidades de saldo
    payload_entrada = {"peca_id": peca_id, "quantidade": 20}
    response = await async_client.post(
        "/estoque/entradas", json=payload_entrada, headers=headers
    )

    # 3. Validações finais de saldo e política de domínio
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["peca_id"] == peca_id
    assert body["quantidade_adicionada"] == 20
    assert body["saldo_anterior"] == 5
    assert body["saldo_atual"] == 25  # 5 + 20
    # Como o novo saldo (25) é superior ou igual ao limite (15), precisa_recompra deve ser False
    assert body["precisa_recompra"] is False


@pytest.mark.asyncio
async def test_registrar_entrada_com_quantidade_invalida_deve_retornar_422(
    async_client: AsyncClient, token_estoquista: str
):
    """
    Cenário: Estoquista tenta registrar entrada com quantidade zero ou negativa.
    Resultado esperado: 422 Unprocessable Entity devido à validação do Schema Pydantic.
    """
    headers = {"Authorization": f"Bearer {token_estoquista}"}
    payload_entrada = {
        "peca_id": str(uuid7()),
        "quantidade": 0,  # Quantidade inválida!
    }
    response = await async_client.post(
        "/estoque/entradas", json=payload_entrada, headers=headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_mecanico_nao_deve_conseguir_registrar_entrada_estoque(
    async_client: AsyncClient, token_mecanico: str
):
    """
    Cenário: Um mecânico tenta registrar entrada no estoque da oficina.
    Resultado esperado: 403 Forbidden pelo controle de segurança por papéis (RBAC).
    """
    headers = {"Authorization": f"Bearer {token_mecanico}"}
    payload_entrada = {"peca_id": str(uuid7()), "quantidade": 10}
    response = await async_client.post(
        "/estoque/entradas", json=payload_entrada, headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_estoquista_deve_conseguir_consultar_relatorio_estoque_baixo_com_sucesso(
    async_client: AsyncClient, token_estoquista: str
):
    """
    Cenário: Estoquista solicita o relatório de itens críticos que precisam de reposição.
    Resultado esperado: 200 OK com os itens que estão abaixo do limite mínimo listados
                        e o custo total calculado corretamente.
    """
    headers = {"Authorization": f"Bearer {token_estoquista}"}

    # 1. Cadastra uma peça segura (quantidade_inicial 20 > limite_minimo 10)
    payload_seguro = {
        "nome": "Aditivo de Radiador TecnoFlu",
        "descricao": "Aditivo de arrefecimento orgânico concentrado",
        "preco_custo": 25.00,
        "preco_venda": 49.90,
        "quantidade_inicial": 20,
        "limite_minimo": 10,
    }
    res_seguro = await async_client.post(
        "/estoque", json=payload_seguro, headers=headers
    )
    assert res_seguro.status_code == status.HTTP_201_CREATED

    # 2. Cadastra uma peça crítica (quantidade_inicial 5 < limite_minimo 15)
    # Déficit: 10 unidades. Custo reposição estimado: 10 * 80.00 = R$ 800.00
    payload_critico = {
        "nome": "Disco de Freio Dianteiro Varga",
        "descricao": "Disco de freio ventilado para utilitários",
        "preco_custo": 80.00,
        "preco_venda": 150.00,
        "quantidade_inicial": 5,
        "limite_minimo": 15,
    }
    res_critico = await async_client.post(
        "/estoque", json=payload_critico, headers=headers
    )
    assert res_critico.status_code == status.HTTP_201_CREATED
    peca_critica_id = res_critico.json()["id"]

    # 3. Solicita o relatório de estoque baixo
    response = await async_client.get("/estoque/relatorios/baixo", headers=headers)

    # 4. Validações analíticas da resposta
    assert response.status_code == status.HTTP_200_OK
    body = response.json()

    assert body["total_itens_criticos"] >= 1
    # Garante que a peça confortável (Aditivo) NÃO está na lista crítica
    nomes_criticos = [item["nome"] for item in body["itens"]]
    assert "Aditivo de Radiador TecnoFlu" not in nomes_criticos

    # Garante que a peça crítica (Disco) está listada com os cálculos corretos
    disco_item = next(item for item in body["itens"] if item["id"] == peca_critica_id)
    assert disco_item["nome"] == "Disco de Freio Dianteiro Varga"
    assert disco_item["quantidade_em_estoque"] == 5
    assert disco_item["limite_minimo"] == 15
    assert disco_item["unidades_em_falta"] == 10
    assert disco_item["preco_custo_referencia"] == "80.00"
    assert disco_item["capital_necessario_reposicao"] == "800.00"


@pytest.mark.asyncio
async def test_gerente_deve_acessar_relatorio_estoque_baixo(
    async_client: AsyncClient, token_gerente: str
):
    """
    Cenário: Gerente acessa o relatório de estoque baixo para planejar fluxo financeiro de compras.
    Resultado esperado: 200 OK com sucesso.
    """
    headers = {"Authorization": f"Bearer {token_gerente}"}
    response = await async_client.get("/estoque/relatorios/baixo", headers=headers)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_mecanico_nao_deve_ter_acesso_ao_relatorio_de_estoque_baixo(
    async_client: AsyncClient, token_mecanico: str
):
    """
    Cenário: Mecânico tenta acessar o relatório financeiro de reabastecimento.
    Resultado esperado: 403 Forbidden (RBAC blinda a informação de faturamento corporativo).
    """
    headers = {"Authorization": f"Bearer {token_mecanico}"}
    response = await async_client.get("/estoque/relatorios/baixo", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
