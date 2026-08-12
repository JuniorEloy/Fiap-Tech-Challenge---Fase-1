import pytest
from fastapi import status
from httpx import AsyncClient
from uuid import uuid7
from validate_docbr import CPF
import random
import string
import base64
import json
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid7, UUID
from app.features.usuarios.models import Usuario
from sqlalchemy import select


def gerar_placa_valida_para_teste() -> str:
    """Gera uma placa Mercosul válida e aleatória (formato AAA9A99) para evitar colisões."""
    leiras_aleatorias_1 = "".join(random.choices(string.ascii_uppercase, k=3))
    numero_1 = str(random.randint(0, 9))
    letra_aleatoria_2 = random.choice(string.ascii_uppercase)
    numeros_finais = "".join(random.choices(string.digits, k=2))

    return f"{leiras_aleatorias_1}{numero_1}{letra_aleatoria_2}{numeros_finais}"


@pytest.mark.asyncio
async def test_recepcionista_deve_abrir_os_com_sucesso_em_diagnostico_quando_nao_houver_servicos(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Recepcionista tenta abrir uma OS padrão sem serviços pré-definidos (ex: "carro falhando").
    Resultado esperado: 201 Created, status EM_DIAGNOSTICO e registros operacionais ativos.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}

    # 0. Cadastramos o usuário operador no banco para satisfazer a FK de auditoria dos logs (os_status_logs)
    payload_usuario = {
        "nome": "Recepcionista Teste",
        "email": "recepcao.teste@oficina.com",
        "senha": "senhaSegura123",
        "role": "RECEPCIONISTA",
    }
    await async_client.post("/usuarios", json=payload_usuario, headers=headers)

    # 1. Cadastramos um cliente de teste com CPF matematicamente válido
    payload_cliente = {
        "nome": "João das Ordens",
        "email": "joao.os@oficina.com",
        "telefone": "11977778888",
        "cpf_cnpj": "32105222862",
        "tipo_pessoa": "FISICA",
    }
    res_cliente = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers
    )
    assert res_cliente.status_code == status.HTTP_201_CREATED
    cliente_id = res_cliente.json()["id"]

    # 2. Cadastramos um veículo para o cliente
    payload_veiculo = {
        "placa": "XYZ-9876",
        "marca": "Chevrolet",
        "modelo": "Onix",
        "ano": 2022,
        "cliente_id": cliente_id,
    }
    res_veiculo = await async_client.post(
        "/veiculos", json=payload_veiculo, headers=headers
    )
    assert res_veiculo.status_code == status.HTTP_201_CREATED
    veiculo_id = res_veiculo.json()["id"]

    # 3. Solicitamos a abertura da OS sem serviços catalogados (demanda diagnóstico mecânico)
    payload_os = {
        "cliente_id": cliente_id,
        "veiculo_id": veiculo_id,
        "servicos": [],
        "pecas": [],
    }

    response = await async_client.post(
        "/ordens-servico", json=payload_os, headers=headers
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert "id" in body
    assert body["cliente_id"] == cliente_id
    assert body["veiculo_id"] == veiculo_id
    assert body["status"] == "EM_DIAGNOSTICO"
    assert body["visualizacao_hash"] is not None


@pytest.mark.asyncio
async def test_gerente_deve_conseguir_abrir_os(
    async_client: AsyncClient, token_gerente: str
):
    """
    Cenário: Gerente tenta abrir uma OS para triagem de pátio.
    Resultado esperado: 201 Created (Gerente herda permissões totais de negócio).
    """
    headers = {"Authorization": f"Bearer {token_gerente}"}

    payload_cliente = {
        "nome": "Marcos Gerência",
        "email": "marcos.gerencia@oficina.com",
        "telefone": "11955556666",
        "cpf_cnpj": "96292365085",
        "tipo_pessoa": "FISICA",
    }
    res_cliente = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers
    )
    assert res_cliente.status_code == status.HTTP_201_CREATED
    cliente_id = res_cliente.json()["id"]

    payload_veiculo = {
        "placa": "MGR-4321",
        "marca": "Toyota",
        "modelo": "Corolla",
        "ano": 2021,
        "cliente_id": cliente_id,
    }
    res_veiculo = await async_client.post(
        "/veiculos", json=payload_veiculo, headers=headers
    )
    assert res_veiculo.status_code == status.HTTP_201_CREATED
    veiculo_id = res_veiculo.json()["id"]

    payload_os = {
        "cliente_id": cliente_id,
        "veiculo_id": veiculo_id,
        "servicos": [],
        "pecas": [],
    }

    response = await async_client.post(
        "/ordens-servico", json=payload_os, headers=headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["status"] == "EM_DIAGNOSTICO"


@pytest.mark.asyncio
async def test_mecanico_nao_deve_conseguir_abrir_os(
    async_client: AsyncClient, token_mecanico: str
):
    """Cenário: Mecânico tenta abrir uma OS (violação de papéis). Resultado: 403 Forbidden."""
    headers = {"Authorization": f"Bearer {token_mecanico}"}
    payload_os = {
        "cliente_id": str(uuid7()),
        "veiculo_id": str(uuid7()),
        "servicos": [],
    }
    response = await async_client.post(
        "/ordens-servico", json=payload_os, headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_estoquista_nao_deve_conseguir_abrir_os(
    async_client: AsyncClient, token_estoquista: str
):
    """Cenário: Estoquista tenta criar uma OS (violação de papel). Resultado: 403 Forbidden."""
    headers = {"Authorization": f"Bearer {token_estoquista}"}
    payload_os = {
        "cliente_id": str(uuid7()),
        "veiculo_id": str(uuid7()),
        "servicos": [],
    }
    response = await async_client.post(
        "/ordens-servico", json=payload_os, headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_usuario_nao_autenticado_deve_receber_401(async_client: AsyncClient):
    """Cenário: Chamada sem token. Resultado: 401 Unauthorized."""
    payload_os = {
        "cliente_id": str(uuid7()),
        "veiculo_id": str(uuid7()),
        "servicos": [],
    }
    response = await async_client.post("/ordens-servico", json=payload_os)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_falha_cliente_nao_encontrado_ao_abrir_os(
    async_client: AsyncClient, token_recepcionista: str
):
    """Cenário: Tentativa de abrir OS com ID de cliente inexistente. Resultado: 404 Not Found."""
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    payload_os = {
        "cliente_id": str(uuid7()),
        "veiculo_id": str(uuid7()),
        "servicos": [],
        "pecas": [],
    }
    response = await async_client.post(
        "/ordens-servico", json=payload_os, headers=headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_falha_veiculo_nao_encontrado_ao_abrir_os(
    async_client: AsyncClient, token_recepcionista: str
):
    """Cenário: Tentativa de abrir OS com cliente válido, mas veículo inexistente. Resultado: 404 Not Found."""
    headers = {"Authorization": f"Bearer {token_recepcionista}"}

    uid = str(uuid7())[:6]
    payload_cliente = {
        "nome": "Cliente Sem Carro",
        "email": f"sem.carro.{uid}@oficina.com",
        "telefone": "11944443333",
        "cpf_cnpj": "52889394034",
        "tipo_pessoa": "FISICA",
    }
    res_cli = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers
    )
    assert res_cli.status_code == status.HTTP_201_CREATED
    cliente_id = res_cli.json()["id"]

    payload_os = {
        "cliente_id": cliente_id,
        "veiculo_id": str(uuid7()),
        "servicos": [],
        "pecas": [],
    }
    response = await async_client.post(
        "/ordens-servico", json=payload_os, headers=headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_falha_servico_inexistente_no_catalogo(
    async_client: AsyncClient, token_recepcionista: str
):
    """Cenário: Tentativa de abrir OS informando um serviço que não existe. Resultado: 400 Bad Request."""
    headers = {"Authorization": f"Bearer {token_recepcionista}"}

    uid = str(uuid7())[:6]
    cpf_valido = CPF().generate()
    placa_valida = gerar_placa_valida_para_teste()

    payload_cliente = {
        "nome": "Cliente Catálogo",
        "email": f"catalogo.{uid}@oficina.com",
        "telefone": "11933332222",
        "cpf_cnpj": cpf_valido,
        "tipo_pessoa": "FISICA",
    }
    res_cli = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers
    )
    assert res_cli.status_code == status.HTTP_201_CREATED
    cliente_id = res_cli.json()["id"]

    payload_vei = {
        "placa": placa_valida,
        "marca": "Fiat",
        "modelo": "Palio",
        "ano": 2010,
        "cliente_id": cliente_id,
    }
    res_vei = await async_client.post("/veiculos", json=payload_vei, headers=headers)
    assert res_vei.status_code == status.HTTP_201_CREATED
    veiculo_id = res_vei.json()["id"]

    payload_os = {
        "cliente_id": cliente_id,
        "veiculo_id": veiculo_id,
        "servicos_solicitados": [{"servico_id": str(uuid7())}],
        "pecas_solicitadas": [],
    }

    response = await async_client.post(
        "/ordens-servico", json=payload_os, headers=headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ==========================================
# NOVOS TESTES PARA COBRIR O FLUXO EXPRESSO (100%)
# ==========================================


@pytest.mark.asyncio
async def test_recepcionista_deve_abrir_os_em_diagnostico_quando_servico_nao_permite_expresso(
    async_client: AsyncClient, token_recepcionista: str, token_gerente: str
):
    """
    Cenário: Serviços informados mas sem permissão de expresso (permite_servico_expresso = False).
    Resultado esperado: 201 Created com status EM_DIAGNOSTICO.
    """
    headers_rec = {"Authorization": f"Bearer {token_recepcionista}"}
    headers_ger = {"Authorization": f"Bearer {token_gerente}"}
    uid = str(uuid7())[:6]

    # 1. Gerente cadastra serviço que NÃO permite expresso
    payload_servico = {
        "nome": f"Retifica de Motor {uid}",
        "descricao": "Serviço complexo de motor",
        "preco_mao_de_obra": 1500.00,
        "duracao_estimada_minutos": 480,
        "permite_servico_expresso": False,
    }
    res_serv = await async_client.post(
        "/servicos", json=payload_servico, headers=headers_ger
    )
    assert res_serv.status_code == status.HTTP_201_CREATED
    servico_id = res_serv.json()["id"]

    # 2. Cadastra cliente e veículo
    res_cli = await async_client.post(
        "/clientes",
        json={
            "nome": "Cliente Motor",
            "email": f"motor.{uid}@oficina.com",
            "telefone": "11911112222",
            "cpf_cnpj": CPF().generate(),
            "tipo_pessoa": "FISICA",
        },
        headers=headers_rec,
    )
    cliente_id = res_cli.json()["id"]

    res_vei = await async_client.post(
        "/veiculos",
        json={
            "placa": gerar_placa_valida_para_teste(),
            "marca": "VW",
            "modelo": "Gol",
            "ano": 2018,
            "cliente_id": cliente_id,
        },
        headers=headers_rec,
    )
    veiculo_id = res_vei.json()["id"]

    # 3. Abre OS solicitando o serviço não expresso
    payload_os = {
        "cliente_id": cliente_id,
        "veiculo_id": veiculo_id,
        "servicos_solicitados": [{"servico_id": servico_id}],
        "pecas_solicitadas": [],
    }
    response = await async_client.post(
        "/ordens-servico", json=payload_os, headers=headers_rec
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["status"] == "EM_DIAGNOSTICO"


@pytest.mark.asyncio
async def test_recepcionista_deve_abrir_os_com_sucesso_em_fluxo_expresso(
    async_client: AsyncClient, token_recepcionista: str, token_gerente: str
):
    """
    Cenário: Serviços com permissão de expresso e peças válidas no estoque.
    Resultado esperado: 201 Created com transição automática para AGUARDANDO_APROVACAO.
    """
    headers_rec = {"Authorization": f"Bearer {token_recepcionista}"}
    headers_ger = {"Authorization": f"Bearer {token_gerente}"}
    uid = str(uuid7())[:6]

    # 1. Gerente cadastra serviço expresso
    res_serv = await async_client.post(
        "/servicos",
        json={
            "nome": f"Alinhamento Rápido {uid}",
            "descricao": "Alinhamento e balanceamento",
            "preco_mao_de_obra": 120.00,
            "duracao_estimada_minutos": 40,
            "permite_servico_expresso": True,
        },
        headers=headers_ger,
    )
    servico_id = res_serv.json()["id"]

    # 2. Gerente cadastra peça no estoque (Rota e Payload Corrigidos)
    res_peca = await async_client.post(
        "/estoque",
        json={
            "nome": f"Chumbo de Roda {uid}",
            "descricao": "Chumbo para balanceamento de rodas",
            "preco_custo": 5.00,
            "preco_venda": 15.00,
            "quantidade_inicial": 50,
            "limite_minimo": 10,
        },
        headers=headers_ger,
    )

    # 3. Cadastra cliente e veículo
    res_cli = await async_client.post(
        "/clientes",
        json={
            "nome": "Cliente Expresso",
            "email": f"expresso.{uid}@oficina.com",
            "telefone": "11922223333",
            "cpf_cnpj": CPF().generate(),
            "tipo_pessoa": "FISICA",
        },
        headers=headers_rec,
    )
    cliente_id = res_cli.json()["id"]

    res_vei = await async_client.post(
        "/veiculos",
        json={
            "placa": gerar_placa_valida_para_teste(),
            "marca": "Honda",
            "modelo": "Civic",
            "ano": 2020,
            "cliente_id": cliente_id,
        },
        headers=headers_rec,
    )
    veiculo_id = res_vei.json()["id"]

    assert res_peca.status_code == status.HTTP_201_CREATED
    peca_id = res_peca.json()["id"]

    # 4. Abre OS com serviço expresso e peça alocada
    payload_os = {
        "cliente_id": cliente_id,
        "veiculo_id": veiculo_id,
        "servicos_solicitados": [{"servico_id": servico_id}],
        "pecas_solicitadas": [{"peca_id": peca_id, "quantidade": 2}],
    }
    response = await async_client.post(
        "/ordens-servico", json=payload_os, headers=headers_rec
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["status"] == "AGUARDANDO_APROVACAO"


@pytest.mark.asyncio
async def test_falha_peca_inexistente_no_estoque_ao_abrir_os(
    async_client: AsyncClient, token_recepcionista: str, token_gerente: str
):
    """
    Cenário: Serviço expresso válido, mas informando peça com ID inexistente no estoque.
    Resultado esperado: 400 Bad Request.
    """
    headers_rec = {"Authorization": f"Bearer {token_recepcionista}"}
    headers_ger = {"Authorization": f"Bearer {token_gerente}"}
    uid = str(uuid7())[:6]

    res_serv = await async_client.post(
        "/servicos",
        json={
            "nome": f"Revisão Básica {uid}",
            "descricao": "Revisão de 10k km",
            "preco_mao_de_obra": 200.00,
            "duracao_estimada_minutos": 60,
            "permite_servico_expresso": True,
        },
        headers=headers_ger,
    )
    servico_id = res_serv.json()["id"]

    res_cli = await async_client.post(
        "/clientes",
        json={
            "nome": "Cliente Peça Errada",
            "email": f"peca.errada.{uid}@oficina.com",
            "telefone": "11933334444",
            "cpf_cnpj": CPF().generate(),
            "tipo_pessoa": "FISICA",
        },
        headers=headers_rec,
    )
    cliente_id = res_cli.json()["id"]

    res_vei = await async_client.post(
        "/veiculos",
        json={
            "placa": gerar_placa_valida_para_teste(),
            "marca": "Hyundai",
            "modelo": "HB20",
            "ano": 2021,
            "cliente_id": cliente_id,
        },
        headers=headers_rec,
    )
    veiculo_id = res_vei.json()["id"]

    payload_os = {
        "cliente_id": cliente_id,
        "veiculo_id": veiculo_id,
        "servicos_solicitados": [{"servico_id": servico_id}],
        "pecas_solicitadas": [{"peca_id": str(uuid7()), "quantidade": 1}],  # Peça fake
    }
    response = await async_client.post(
        "/ordens-servico", json=payload_os, headers=headers_rec
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def gerar_placa_valida_para_teste() -> str:
    """Gera uma placa Mercosul válida e aleatória (formato AAA9A99) para evitar colisões."""
    letras_aleatorias_1 = "".join(random.choices(string.ascii_uppercase, k=3))
    numero_1 = str(random.randint(0, 9))
    letra_aleatoria_2 = random.choice(string.ascii_uppercase)
    numeros_finais = "".join(random.choices(string.digits, k=2))
    return f"{letras_aleatorias_1}{numero_1}{letra_aleatoria_2}{numeros_finais}"


async def garantir_usuario_existe_no_banco(
    token: str, role: str, db: AsyncSession, uid: str
) -> str:
    """Decodifica o payload do JWT, obtém o sub (UUID) e insere fisicamente na tabela usuarios se não existir."""
    token_parts = token.split(".")
    payload_decoded = base64.b64decode(token_parts[1] + "==").decode("utf-8")
    payload_json = json.loads(payload_decoded)
    user_id = payload_json["sub"]

    res = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user_db = res.scalar_one_or_none()
    if not user_db:
        new_user = Usuario(
            id=UUID(user_id),
            nome=f"Usuario Teste {role.capitalize()} {uid}",
            email=f"{role.lower()}.{uid}@oficina.com",
            role=role,
            ativo=True,
        )
        db.add(new_user)
        await db.commit()
    return user_id


@pytest.mark.asyncio
async def test_mecanico_deve_lancar_diagnostico_com_sucesso(
    async_client: AsyncClient,
    token_recepcionista: str,
    token_estoquista: str,
    token_mecanico: str,
    db: AsyncSession,
):
    """
    Cenário: Mecânico assume o veículo em triagem, identifica anomalias físicas,
             e lança o diagnóstico com serviços e peças do catálogo.
    Resultado esperado: 200 OK, OS alterada para AGUARDANDO_APROVACAO com preços congelados.
    """
    headers_recep = {"Authorization": f"Bearer {token_recepcionista}"}
    headers_estoque = {"Authorization": f"Bearer {token_estoquista}"}
    headers_meca = {"Authorization": f"Bearer {token_mecanico}"}

    uid = str(uuid7())[:6]

    # Garante que os usuários reais dos tokens existam fisicamente no banco de dados para evitar ForeignKeyViolation
    await garantir_usuario_existe_no_banco(
        token_recepcionista, "RECEPCIONISTA", db, uid
    )
    await garantir_usuario_existe_no_banco(token_estoquista, "ESTOQUISTA", db, uid)
    mecanico_id = await garantir_usuario_existe_no_banco(
        token_mecanico, "MECANICO", db, uid
    )

    # 1. Recepção cadastra o cliente (usando CPF matematicamente válido)
    payload_cliente = {
        "nome": f"Carla Souza Diagnostico {uid}",
        "email": f"carla.diagnostico.{uid}@gmail.com",
        "telefone": "11988887777",
        "cpf_cnpj": CPF().generate(),
        "tipo_pessoa": "FISICA",
    }
    res_cliente = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers_recep
    )
    assert res_cliente.status_code == status.HTTP_201_CREATED
    cliente_id = res_cliente.json()["id"]

    # 2. Recepção cadastra o veículo
    payload_veiculo = {
        "placa": gerar_placa_valida_para_teste(),
        "marca": "Honda",
        "modelo": "Civic",
        "ano": 2021,
        "cliente_id": cliente_id,
    }
    res_veiculo = await async_client.post(
        "/veiculos", json=payload_veiculo, headers=headers_recep
    )
    assert res_veiculo.status_code == status.HTTP_201_CREATED
    veiculo_id = res_veiculo.json()["id"]

    # 3. Recepção cadastra um Serviço Base padrão no catálogo
    payload_servico = {
        "nome": f"Troca de Velas e Bobinas {uid}",
        "descricao": "Substituição preventiva do sistema de ignição",
        "preco_mao_de_obra": 150.00,
        "duracao_estimada_minutos": 45,
        "permite_servico_expresso": False,
    }
    res_servico = await async_client.post(
        "/servicos", json=payload_servico, headers=headers_recep
    )
    assert res_servico.status_code == status.HTTP_201_CREATED
    servico_id = res_servico.json()["id"]

    # 4. Estoquista cadastra as peças no estoque
    payload_peca = {
        "nome": f"Jogo de Velas Iridium NGK {uid}",
        "descricao": "Velas de ignição de alta performance e longa durabilidade",
        "preco_custo": 80.00,
        "preco_venda": 160.00,
        "quantidade_inicial": 10,
        "limite_minimo": 3,
    }
    res_peca = await async_client.post(
        "/estoque", json=payload_peca, headers=headers_estoque
    )
    assert res_peca.status_code == status.HTTP_201_CREATED
    peca_id = res_peca.json()["id"]

    # 5. Recepção efetua o Check-in abrindo a OS vazia (sem serviços)
    # Como não há itens na abertura, ela cai obrigatoriamente em "EM_DIAGNOSTICO"
    payload_os = {
        "cliente_id": cliente_id,
        "veiculo_id": veiculo_id,
        "servicos": [],
        "pecas": [],
    }
    res_os = await async_client.post(
        "/ordens-servico", json=payload_os, headers=headers_recep
    )
    assert res_os.status_code == status.HTTP_201_CREATED
    os_id = res_os.json()["id"]
    assert res_os.json()["status"] == "EM_DIAGNOSTICO"

    # 6. Mecânico executa a desmontagem física e lança o diagnóstico técnico
    payload_diagnostico = {
        "servicos": [{"servico_id": servico_id}],
        "pecas": [{"peca_id": peca_id, "quantidade": 1}],
    }

    response = await async_client.put(
        f"/ordens-servico/{os_id}/diagnostico",
        json=payload_diagnostico,
        headers=headers_meca,
    )

    # 7. Asserções de sucesso do diagnóstico
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == os_id
    assert body["status"] == "AGUARDANDO_APROVACAO"  # FSM transicionou automaticamente!
    assert body["mecanico_id"] == mecanico_id  # Mecânico foi amarrado à OS

    # Verifica o congelamento de preços de serviços
    assert len(body["itens_servico"]) == 1
    assert body["itens_servico"][0]["servico_id"] == servico_id
    assert body["itens_servico"][0]["preco_aplicado"] == "150.00"
    assert body["itens_servico"][0]["duracao_minutos"] == 45

    # Verifica o congelamento de preços de peças de estoque
    assert len(body["itens_peca"]) == 1
    assert body["itens_peca"][0]["peca_id"] == peca_id
    assert body["itens_peca"][0]["preco_unitario_aplicado"] == "160.00"
    assert body["itens_peca"][0]["quantidade"] == 1


@pytest.mark.asyncio
async def test_recepcionista_nao_deve_conseguir_lancar_diagnostico(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Recepcionista tenta lançar o laudo de diagnóstico (violação de papéis).
    Resultado esperado: 403 Forbidden (RBAC blinda o endpoint).
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    os_id_fake = str(uuid7())
    payload = {"servicos": [{"servico_id": str(uuid7())}], "pecas": []}

    response = await async_client.put(
        f"/ordens-servico/{os_id_fake}/diagnostico", json=payload, headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_mecanico_deve_visualizar_apenas_suas_ordens_de_servico_ativas(
    async_client: AsyncClient,
    token_recepcionista: str,
    token_mecanico: str,
    db: AsyncSession,
):
    """
    Cenário: Mecânico acessa seu painel pessoal de trabalho.
    Resultado esperado: 200 OK contendo apenas OSs atribuídas a ele em DIAGNÓSTICO ou EXECUÇÃO.
    """
    headers_recep = {"Authorization": f"Bearer {token_recepcionista}"}
    headers_meca = {"Authorization": f"Bearer {token_mecanico}"}

    uid = str(uuid7())[:6]

    # Garante que os usuários reais existam
    await garantir_usuario_existe_no_banco(
        token_recepcionista, "RECEPCIONISTA", db, uid
    )
    mecanico_id = await garantir_usuario_existe_no_banco(
        token_mecanico, "MECANICO", db, uid
    )

    # 1. Criamos um cliente e veículo
    payload_cliente = {
        "nome": f"Marcos Lima Painel {uid}",
        "email": f"marcos.painel.{uid}@gmail.com",
        "telefone": "11977776666",
        "cpf_cnpj": CPF().generate(),
        "tipo_pessoa": "FISICA",
    }
    res_cliente = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers_recep
    )
    cliente_id = res_cliente.json()["id"]

    payload_veiculo = {
        "placa": gerar_placa_valida_para_teste(),
        "marca": "Fiat",
        "modelo": "Marea Turbo",
        "ano": 2005,
        "cliente_id": cliente_id,
    }
    res_veiculo = await async_client.post(
        "/veiculos", json=payload_veiculo, headers=headers_recep
    )
    veiculo_id = res_veiculo.json()["id"]

    # 2. Criamos um Serviço Base no catálogo
    payload_serv = {
        "nome": f"Inspeção de Turbina {uid}",
        "descricao": "Varredura de folgas em eixos de compressor",
        "preco_mao_de_obra": 200.00,
        "duracao_estimada_minutos": 60,
        "permite_servico_expresso": False,
    }
    res_serv = await async_client.post(
        "/servicos", json=payload_serv, headers=headers_recep
    )
    servico_id = res_serv.json()["id"]

    # 3. Abre-se a OS
    payload_os = {
        "cliente_id": cliente_id,
        "veiculo_id": veiculo_id,
        "servicos": [],
        "pecas": [],
    }
    res_os = await async_client.post(
        "/ordens-servico", json=payload_os, headers=headers_recep
    )
    os_id = res_os.json()["id"]

    # 4. Mecânico acessa a lista "minhas-os" - Deve vir vazia inicialmente pois nenhuma OS está atribuída a ele
    res_lista_inicial = await async_client.get(
        "/ordens-servico/mecanico/minhas-os", headers=headers_meca
    )
    assert res_lista_inicial.status_code == status.HTTP_200_OK
    assert os_id not in [item["id"] for item in res_lista_inicial.json()]

    # 5. Mecânico assume a OS realizando o diagnóstico (o handler atrela o mecanico_id a ele!)
    payload_diagnostico = {"servicos": [{"servico_id": servico_id}], "pecas": []}
    await async_client.put(
        f"/ordens-servico/{os_id}/diagnostico",
        json=payload_diagnostico,
        headers=headers_meca,
    )

    # 6. Agora a OS está no status AGUARDANDO_APROVACAO (não deve aparecer no painel operacional de pátio!)
    res_lista_pos_diagnostico = await async_client.get(
        "/ordens-servico/mecanico/minhas-os", headers=headers_meca
    )
    assert res_lista_pos_diagnostico.status_code == status.HTTP_200_OK
    assert os_id not in [item["id"] for item in res_lista_pos_diagnostico.json()]
