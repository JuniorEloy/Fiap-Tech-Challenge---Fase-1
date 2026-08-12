import pytest
from fastapi import status
from httpx import AsyncClient
from uuid import uuid7
from validate_docbr import CPF
import random
import string
import base64
import json
from uuid import uuid7, UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.usuarios.models import Usuario
from app.features.estoque.models import PecaInsumo
from app.features.ordens_servico.models import StatusOS, OrdemServico


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
async def test_cliente_deve_aprovar_orcamento_com_sucesso_via_portal_publico(
    async_client: AsyncClient,
    token_recepcionista: str,
    token_estoquista: str,
    token_mecanico: str,
    db: AsyncSession,
):
    """
    Cenário: Orçamento emitido em diagnóstico e enviado ao cliente. O cliente
             acessa o link público (com hash), aprova o orçamento e o sistema
             baixa o estoque pessimamente, passando a OS para EM_EXECUCAO.
    Resultado esperado: 200 OK, status mudado para EM_EXECUCAO e estoque decrementado.
    """
    headers_recep = {"Authorization": f"Bearer {token_recepcionista}"}
    headers_estoque = {"Authorization": f"Bearer {token_estoquista}"}
    headers_meca = {"Authorization": f"Bearer {token_mecanico}"}

    uid = str(uuid7())[:6]

    # Garante que os usuários do token existam na tabela usuarios
    await garantir_usuario_existe_no_banco(
        token_recepcionista, "RECEPCIONISTA", db, uid
    )
    await garantir_usuario_existe_no_banco(token_estoquista, "ESTOQUISTA", db, uid)
    await garantir_usuario_existe_no_banco(token_mecanico, "MECANICO", db, uid)

    # 1. Cadastra Cliente e Veículo
    payload_cliente = {
        "nome": f"Rodrigo Aprovador {uid}",
        "email": f"rodrigo.aprovador.{uid}@gmail.com",
        "telefone": "11988887777",
        "cpf_cnpj": CPF().generate(),
        "tipo_pessoa": "FISICA",
    }
    res_cliente = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers_recep
    )
    assert res_cliente.status_code == status.HTTP_201_CREATED
    cliente_id = res_cliente.json()["id"]

    payload_veiculo = {
        "placa": gerar_placa_valida_para_teste(),
        "marca": "Toyota",
        "modelo": "Yaris",
        "ano": 2022,
        "cliente_id": cliente_id,
    }
    res_veiculo = await async_client.post(
        "/veiculos", json=payload_veiculo, headers=headers_recep
    )
    assert res_veiculo.status_code == status.HTTP_201_CREATED
    veiculo_id = res_veiculo.json()["id"]

    # 2. Cadastra Serviço e Peça de Estoque
    payload_servico = {
        "nome": f"Revisão Completa Yaris {uid}",
        "descricao": "Troca de filtros e fluidos gerais",
        "preco_mao_de_obra": 300.00,
        "duracao_estimada_minutos": 120,
        "permite_servico_expresso": False,
    }
    res_servico = await async_client.post(
        "/servicos", json=payload_servico, headers=headers_recep
    )
    assert res_servico.status_code == status.HTTP_201_CREATED
    servico_id = res_servico.json()["id"]

    payload_peca = {
        "nome": f"Filtro de Óleo Bosch Yaris {uid}",
        "descricao": "Filtro de óleo blindado Bosch",
        "preco_custo": 25.00,
        "preco_venda": 60.00,
        "quantidade_inicial": 10,
        "limite_minimo": 2,
    }
    res_peca = await async_client.post(
        "/estoque", json=payload_peca, headers=headers_estoque
    )
    assert res_peca.status_code == status.HTTP_201_CREATED
    peca_id = res_peca.json()["id"]

    # 3. Abre a OS na triagem (vazia, EM_DIAGNOSTICO)
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
    visualizacao_hash = res_os.json()["visualizacao_hash"]

    # 4. Mecânico preenche o laudo técnico do diagnóstico
    payload_diagnostico = {
        "servicos": [{"servico_id": servico_id}],
        "pecas": [{"peca_id": peca_id, "quantidade": 2}],
    }
    res_diag = await async_client.put(
        f"/ordens-servico/{os_id}/diagnostico",
        json=payload_diagnostico,
        headers=headers_meca,
    )
    assert res_diag.status_code == status.HTTP_200_OK
    assert res_diag.json()["status"] == "AGUARDANDO_APROVACAO"

    # 5. Cliente acessa o link público com o hash e responde "Aprovado"
    payload_resposta = {
        "aprovado": True,
        "observacoes_cliente": "Pode fazer o serviço, preciso do carro até amanhã às 18h!",
    }
    response = await async_client.post(
        f"/ordens-servico/publica/{visualizacao_hash}/responder", json=payload_resposta
    )
    assert response.status_code == status.HTTP_200_OK

    body = response.json()
    assert body["status"] == "EM_EXECUCAO"
    assert (
        body["observacoes_cliente"]
        == "Pode fazer o serviço, preciso do carro até amanhã às 18h!"
    )
    assert body["data_resposta_cliente"] is not None
    assert body["tempo_espera_aprovacao_minutos"] is not None

    # 6. Verifica se a baixa de estoque com lock pessimista ocorreu com precisão
    db.expire_all()
    res_peca_db = await db.execute(select(PecaInsumo).where(PecaInsumo.id == peca_id))
    peca_final = res_peca_db.scalar_one()
    # Tinha 10 unidades, foram usadas 2. Sobram 8.
    assert peca_final.quantidade_em_estoque == 8


@pytest.mark.asyncio
async def test_recepcionista_deve_registrar_rejeicao_do_cliente_por_telefone(
    async_client: AsyncClient,
    token_recepcionista: str,
    token_estoquista: str,
    token_mecanico: str,
    db: AsyncSession,
):
    """
    Cenário: O orçamento foi emitido, o cliente rejeita o orçamento por telefone,
             e a Recepcionista registra a rejeição no painel da oficina.
    Resultado esperado: 200 OK, status transiciona para CANCELADA e o estoque não é alterado.
    """
    headers_recep = {"Authorization": f"Bearer {token_recepcionista}"}
    headers_estoque = {"Authorization": f"Bearer {token_estoquista}"}
    headers_meca = {"Authorization": f"Bearer {token_mecanico}"}

    uid = str(uuid7())[:6]

    await garantir_usuario_existe_no_banco(
        token_recepcionista, "RECEPCIONISTA", db, uid
    )
    await garantir_usuario_existe_no_banco(token_estoquista, "ESTOQUISTA", db, uid)
    await garantir_usuario_existe_no_banco(token_mecanico, "MECANICO", db, uid)

    # 1. Cadastra Cliente e Veículo
    payload_cliente = {
        "nome": f"Cláudio Rejeitador {uid}",
        "email": f"claudio.{uid}@gmail.com",
        "telefone": "11966665555",
        "cpf_cnpj": CPF().generate(),
        "tipo_pessoa": "FISICA",
    }
    res_cli = await async_client.post(
        "/clientes", json=payload_cliente, headers=headers_recep
    )
    cliente_id = res_cli.json()["id"]

    payload_veiculo = {
        "placa": gerar_placa_valida_para_teste(),
        "marca": "Ford",
        "modelo": "Ka",
        "ano": 2018,
        "cliente_id": cliente_id,
    }
    res_vei = await async_client.post(
        "/veiculos", json=payload_veiculo, headers=headers_recep
    )
    veiculo_id = res_vei.json()["id"]

    # 2. Cadastra Serviço e Peça de Estoque
    res_serv = await async_client.post(
        "/servicos",
        json={
            "nome": f"Troca de Disco de Freio {uid}",
            "preco_mao_de_obra": 150.00,
            "duracao_estimada_minutos": 60,
            "permite_servico_expresso": False,
        },
        headers=headers_recep,
    )
    servico_id = res_serv.json()["id"]

    res_peca = await async_client.post(
        "/estoque",
        json={
            "nome": f"Par de Discos Freio Bosch {uid}",
            "preco_custo": 90.00,
            "preco_venda": 180.00,
            "quantidade_inicial": 5,
            "limite_minimo": 1,
        },
        headers=headers_estoque,
    )
    peca_id = res_peca.json()["id"]

    # 3. Abre OS e lança diagnóstico
    res_os = await async_client.post(
        "/ordens-servico",
        json={"cliente_id": cliente_id, "veiculo_id": veiculo_id},
        headers=headers_recep,
    )
    os_id = res_os.json()["id"]

    await async_client.put(
        f"/ordens-servico/{os_id}/diagnostico",
        json={
            "servicos": [{"servico_id": servico_id}],
            "pecas": [{"peca_id": peca_id, "quantidade": 1}],
        },
        headers=headers_meca,
    )

    # 4. Recepcionista registra a rejeição do cliente
    payload_rejeicao = {
        "aprovado": False,
        "observacoes_cliente": "Cliente achou o valor muito alto e fará no próximo mês.",
    }
    response = await async_client.post(
        f"/ordens-servico/{os_id}/resposta",
        json=payload_rejeicao,
        headers=headers_recep,
    )
    assert response.status_code == status.HTTP_200_OK

    body = response.json()
    assert body["status"] == "CANCELADA"
    assert (
        body["observacoes_cliente"]
        == "Cliente achou o valor muito alto e fará no próximo mês."
    )

    # 5. Garante que nenhuma peça foi retirada do estoque
    db.expire_all()
    res_peca_db = await db.execute(select(PecaInsumo).where(PecaInsumo.id == peca_id))
    peca_final = res_peca_db.scalar_one()
    # Continuou com as 5 iniciais
    assert peca_final.quantidade_em_estoque == 5


@pytest.mark.asyncio
async def test_falha_na_aprovacao_se_estoque_for_insuficiente(
    async_client: AsyncClient,
    token_recepcionista: str,
    token_estoquista: str,
    token_mecanico: str,
    db: AsyncSession,
):
    """
    Cenário: O diagnóstico demanda 5 peças de reposição, mas o estoque possui apenas 3 unidades.
             O cliente tenta aprovar a execução.
    Resultado esperado: 400 Bad Request, informando o saldo insuficiente, mantendo a OS em AGUARDANDO_APROVACAO.
    """
    headers_recep = {"Authorization": f"Bearer {token_recepcionista}"}
    headers_estoque = {"Authorization": f"Bearer {token_estoquista}"}
    headers_meca = {"Authorization": f"Bearer {token_mecanico}"}

    uid = str(uuid7())[:6]

    await garantir_usuario_existe_no_banco(
        token_recepcionista, "RECEPCIONISTA", db, uid
    )
    await garantir_usuario_existe_no_banco(token_estoquista, "ESTOQUISTA", db, uid)
    await garantir_usuario_existe_no_banco(token_mecanico, "MECANICO", db, uid)

    # 1. Criação do cliente e veículo
    res_cli = await async_client.post(
        "/clientes",
        json={
            "nome": f"Estoque Falho {uid}",
            "email": f"estoque.{uid}@gmail.com",
            "telefone": "11955554444",
            "cpf_cnpj": CPF().generate(),
            "tipo_pessoa": "FISICA",
        },
        headers=headers_recep,
    )
    cliente_id = res_cli.json()["id"]

    res_vei = await async_client.post(
        "/veiculos",
        json={
            "placa": gerar_placa_valida_para_teste(),
            "marca": "Chevrolet",
            "modelo": "Cruze",
            "ano": 2019,
            "cliente_id": cliente_id,
        },
        headers=headers_recep,
    )
    veiculo_id = res_vei.json()["id"]

    # 2. Criação do catálogo (Temos apenas 3 amortecedores em estoque)
    res_serv = await async_client.post(
        "/servicos",
        json={
            "nome": f"Troca de Amortecedores Dianteiros {uid}",
            "preco_mao_de_obra": 200.00,
            "duracao_estimada_minutos": 90,
            "permite_servico_expresso": False,
        },
        headers=headers_recep,
    )
    servico_id = res_serv.json()["id"]

    res_peca = await async_client.post(
        "/estoque",
        json={
            "nome": f"Amortecedor Cofap Cruze {uid}",
            "preco_custo": 150.00,
            "preco_venda": 350.00,
            "quantidade_inicial": 3,  # 🌟 Estoque real: 3 unidades
            "limite_minimo": 1,
        },
        headers=headers_estoque,
    )
    peca_id = res_peca.json()["id"]

    # 3. Abre OS e diagnóstico (solicitando 4 amortecedores - acima do estoque)
    res_os = await async_client.post(
        "/ordens-servico",
        json={"cliente_id": cliente_id, "veiculo_id": veiculo_id},
        headers=headers_recep,
    )
    os_id = res_os.json()["id"]
    visualizacao_hash = res_os.json()["visualizacao_hash"]

    # Mecânico põe 4 amortecedores no diagnóstico
    await async_client.put(
        f"/ordens-servico/{os_id}/diagnostico",
        json={
            "servicos": [{"servico_id": servico_id}],
            "pecas": [{"peca_id": peca_id, "quantidade": 4}],
        },
        headers=headers_meca,
    )

    # 4. Cliente tenta aprovar
    response = await async_client.post(
        f"/ordens-servico/publica/{visualizacao_hash}/responder",
        json={"aprovado": True},
    )

    # Deve falhar pois o pátio não possui peças físicas para suportar a aprovação!
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Saldo insuficiente no estoque" in response.json()["detail"]

    # 5. Garante que o status da OS continuou inalterado e o estoque intocado
    db.expire_all()
    res_os_db = await db.execute(select(OrdemServico).where(OrdemServico.id == os_id))
    os_final = res_os_db.scalar_one()
    assert os_final.status == StatusOS.AGUARDANDO_APROVACAO

    res_peca_db = await db.execute(select(PecaInsumo).where(PecaInsumo.id == peca_id))
    peca_final = res_peca_db.scalar_one()
    assert peca_final.quantidade_em_estoque == 3


@pytest.mark.asyncio
async def test_mecanico_nao_deve_conseguir_registrar_resposta_de_cliente(
    async_client: AsyncClient, token_mecanico: str
):
    """
    Cenário: Mecânico tenta atualizar a resposta do cliente usando o ID da OS (violação de RBAC).
    Resultado esperado: 403 Forbidden.
    """
    headers = {"Authorization": f"Bearer {token_mecanico}"}
    payload = {"aprovado": True}

    response = await async_client.post(
        f"/ordens-servico/{uuid7()}/resposta", json=payload, headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


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
async def test_mecanico_deve_finalizar_os_com_sucesso(
    async_client: AsyncClient,
    token_recepcionista: str,
    token_estoquista: str,
    token_mecanico: str,
    db: AsyncSession,
):
    """
    Cenário: Uma OS é aberta, diagnosticada, aprovada pelo cliente (entra em EM_EXECUCAO)
             e o mecânico registra a conclusão do serviço técnico.
    Resultado esperado: 200 OK, status FINALIZADA, data de conclusão gravada,
                        leadtimes (KPIs) calculados e faturamento fechado de forma íntegra.
    """
    headers_recep = {"Authorization": f"Bearer {token_recepcionista}"}
    headers_estoque = {"Authorization": f"Bearer {token_estoquista}"}
    headers_meca = {"Authorization": f"Bearer {token_mecanico}"}

    uid = str(uuid7())[:6]

    # Garante usuários físicos no banco
    await garantir_usuario_existe_no_banco(
        token_recepcionista, "RECEPCIONISTA", db, uid
    )
    await garantir_usuario_existe_no_banco(token_estoquista, "ESTOQUISTA", db, uid)
    mecanico_id = await garantir_usuario_existe_no_banco(
        token_mecanico, "MECANICO", db, uid
    )

    # 1. Cadastra Cliente e Veículo
    res_cliente = await async_client.post(
        "/clientes",
        json={
            "nome": f"Danilo Executor {uid}",
            "email": f"danilo.{uid}@gmail.com",
            "telefone": "11933334444",
            "cpf_cnpj": CPF().generate(),
            "tipo_pessoa": "FISICA",
        },
        headers=headers_recep,
    )
    cliente_id = res_cliente.json()["id"]

    res_veiculo = await async_client.post(
        "/veiculos",
        json={
            "placa": gerar_placa_valida_para_teste(),
            "marca": "Nissan",
            "modelo": "Versa",
            "ano": 2021,
            "cliente_id": cliente_id,
        },
        headers=headers_recep,
    )
    veiculo_id = res_veiculo.json()["id"]

    # 2. Cadastra Serviços e Peças no Catálogo
    res_serv = await async_client.post(
        "/servicos",
        json={
            "nome": f"Revisão de Freios {uid}",
            "descricao": "Troca de pastilhas e discos",
            "preco_mao_de_obra": 180.00,
            "duracao_estimada_minutos": 60,
            "permite_servico_expresso": False,
        },
        headers=headers_recep,
    )
    servico_id = res_serv.json()["id"]

    res_peca = await async_client.post(
        "/estoque",
        json={
            "nome": f"Pastilhas Freio Versa {uid}",
            "preco_custo": 40.00,
            "preco_venda": 110.00,
            "quantidade_inicial": 10,
            "limite_minimo": 2,
        },
        headers=headers_estoque,
    )
    peca_id = res_peca.json()["id"]

    # 3. Abre OS e lança laudo de Diagnóstico
    res_os = await async_client.post(
        "/ordens-servico",
        json={"cliente_id": cliente_id, "veiculo_id": veiculo_id},
        headers=headers_recep,
    )
    os_id = res_os.json()["id"]
    visualizacao_hash = res_os.json()["visualizacao_hash"]

    await async_client.put(
        f"/ordens-servico/{os_id}/diagnostico",
        json={
            "servicos": [{"servico_id": servico_id}],
            "pecas": [{"peca_id": peca_id, "quantidade": 2}],
        },
        headers=headers_meca,
    )

    # 4. Cliente realiza a aprovação do orçamento (OS transiciona para EM_EXECUCAO)
    res_aprov = await async_client.post(
        f"/ordens-servico/publica/{visualizacao_hash}/responder",
        json={"aprovado": True, "observacoes_cliente": "Aprovado, favor caprichar!"},
    )
    assert res_aprov.status_code == status.HTTP_200_OK
    assert res_aprov.json()["status"] == "EM_EXECUCAO"

    # 5. Mecânico finaliza os serviços
    payload_finalizar = {
        "observacoes_finais": "Serviço realizado com sucesso. Freios limpos e pastilhas trocadas."
    }
    response = await async_client.post(
        f"/ordens-servico/{os_id}/finalizar",
        json=payload_finalizar,
        headers=headers_meca,
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()

    # Asserções de estado e KPIs
    assert body["status"] == "FINALIZADA"
    assert body["data_conclusao"] is not None
    assert body["leadtime_full_minutos"] >= 0
    assert body["leadtime_ativo_minutos"] >= 0

    # Asserções de Faturamento Financeiro (Consolidado e congelado)
    # Serviços: 1x Revisão de Freios = 180.00
    # Peças: 2x Pastilhas de Freio (110.00 cada) = 220.00
    # Total esperado: 180.00 + 220.00 = 400.00
    assert body["valor_servicos"] == "180.00"
    assert body["valor_pecas"] == "220.00"
    assert body["valor_total"] == "400.00"


@pytest.mark.asyncio
async def test_recepcionista_nao_deve_conseguir_finalizar_os(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Recepcionista tenta chamar a rota de conclusão técnica de OS (violação de RBAC).
    Resultado esperado: 403 Forbidden.
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    payload = {"observacoes_finais": "Tenta finalizar"}

    response = await async_client.post(
        f"/ordens-servico/{uuid7()}/finalizar", json=payload, headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_falha_ao_finalizar_os_que_nao_esta_em_execucao(
    async_client: AsyncClient,
    token_recepcionista: str,
    token_mecanico: str,
    db: AsyncSession,
):
    """
    Cenário: Uma OS é aberta na triagem (RECEBIDA -> EM_DIAGNOSTICO). O mecânico
             tenta finalizá-la diretamente sem antes obter a aprovação do cliente.
    Resultado esperado: 400 Bad Request, violando as regras da máquina de estados.
    """
    headers_recep = {"Authorization": f"Bearer {token_recepcionista}"}
    headers_meca = {"Authorization": f"Bearer {token_mecanico}"}

    uid = str(uuid7())[:6]

    await garantir_usuario_existe_no_banco(
        token_recepcionista, "RECEPCIONISTA", db, uid
    )
    await garantir_usuario_existe_no_banco(token_mecanico, "MECANICO", db, uid)

    # Cadastra cliente e veículo
    res_cliente = await async_client.post(
        "/clientes",
        json={
            "nome": f"Claudio Bloqueado {uid}",
            "email": f"claudio.bloq.{uid}@gmail.com",
            "telefone": "11922223333",
            "cpf_cnpj": CPF().generate(),
            "tipo_pessoa": "FISICA",
        },
        headers=headers_recep,
    )
    cliente_id = res_cliente.json()["id"]

    res_veiculo = await async_client.post(
        "/veiculos",
        json={
            "placa": gerar_placa_valida_para_teste(),
            "marca": "Nissan",
            "modelo": "March",
            "ano": 2018,
            "cliente_id": cliente_id,
        },
        headers=headers_recep,
    )
    veiculo_id = res_veiculo.json()["id"]

    # Abre a OS (Fica em EM_DIAGNOSTICO)
    res_os = await async_client.post(
        "/ordens-servico",
        json={"cliente_id": cliente_id, "veiculo_id": veiculo_id},
        headers=headers_recep,
    )
    os_id = res_os.json()["id"]

    # Tenta finalizar de forma ilegal (transição inválida)
    response = await async_client.post(
        f"/ordens-servico/{os_id}/finalizar",
        json={"observacoes_finais": "Bypassing state machine"},
        headers=headers_meca,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        "Não é possível concluir uma OS que não está em execução"
        in response.json()["detail"]
    )


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
async def test_recepcionista_deve_registrar_pagamento_e_entrega_com_sucesso(
    async_client: AsyncClient,
    token_recepcionista: str,
    token_estoquista: str,
    token_mecanico: str,
    db: AsyncSession,
):
    """
    Cenário: Uma OS passa por todo o ciclo operacional até ser FINALIZADA. No caixa,
             a Recepcionista registra o pagamento (PIX) e autoriza a entrega final.
    Resultado esperado: 200 OK, transição para status ENTREGUE, cálculo exato do faturamento
                        final consolidado e registro dos dados do Caixa.
    """
    headers_recep = {"Authorization": f"Bearer {token_recepcionista}"}
    headers_estoque = {"Authorization": f"Bearer {token_estoquista}"}
    headers_meca = {"Authorization": f"Bearer {token_mecanico}"}

    uid = str(uuid7())[:6]

    # Garante usuários nos tokens persistidos
    await garantir_usuario_existe_no_banco(
        token_recepcionista, "RECEPCIONISTA", db, uid
    )
    await garantir_usuario_existe_no_banco(token_estoquista, "ESTOQUISTA", db, uid)
    await garantir_usuario_existe_no_banco(token_mecanico, "MECANICO", db, uid)

    # 1. Cadastra Cliente e Veículo
    res_cli = await async_client.post(
        "/clientes",
        json={
            "nome": f"Marcos Pagador {uid}",
            "email": f"marcos.pagador.{uid}@gmail.com",
            "telefone": "11988887777",
            "cpf_cnpj": CPF().generate(),
            "tipo_pessoa": "FISICA",
        },
        headers=headers_recep,
    )
    cliente_id = res_cli.json()["id"]

    res_vei = await async_client.post(
        "/veiculos",
        json={
            "placa": gerar_placa_valida_para_teste(),
            "marca": "Chevrolet",
            "modelo": "Cruze",
            "ano": 2020,
            "cliente_id": cliente_id,
        },
        headers=headers_recep,
    )
    veiculo_id = res_vei.json()["id"]

    # 2. Cadastra catálogo de Serviços e Peças
    res_serv = await async_client.post(
        "/servicos",
        json={
            "nome": f"Troca de Kit de Embreagem {uid}",
            "descricao": "Substituição completa do platô, disco e rolamento",
            "preco_mao_de_obra": 400.00,
            "duracao_estimada_minutos": 180,
            "permite_servico_expresso": False,
        },
        headers=headers_recep,
    )
    servico_id = res_serv.json()["id"]

    res_peca = await async_client.post(
        "/estoque",
        json={
            "nome": f"Kit Embreagem LUK Cruze {uid}",
            "descricao": "Kit de embreagem LUK original",
            "preco_custo": 350.00,
            "preco_venda": 650.00,
            "quantidade_inicial": 5,
            "limite_minimo": 1,
        },
        headers=headers_estoque,
    )
    peca_id = res_peca.json()["id"]

    # 3. Abre OS (RECEBIDA -> EM_DIAGNOSTICO)
    res_os = await async_client.post(
        "/ordens-servico",
        json={
            "cliente_id": cliente_id,
            "veiculo_id": veiculo_id,
            "servicos": [],
            "pecas": [],
        },
        headers=headers_recep,
    )
    os_id = res_os.json()["id"]
    visualizacao_hash = res_os.json()["visualizacao_hash"]

    # 4. Mecânico lança o laudo de diagnóstico (EM_DIAGNOSTICO -> AGUARDANDO_APROVACAO)
    await async_client.put(
        f"/ordens-servico/{os_id}/diagnostico",
        json={
            "servicos": [{"servico_id": servico_id}],
            "pecas": [{"peca_id": peca_id, "quantidade": 1}],
        },
        headers=headers_meca,
    )

    # 5. Cliente aprova o orçamento (AGUARDANDO_APROVACAO -> EM_EXECUCAO)
    await async_client.post(
        f"/ordens-servico/publica/{visualizacao_hash}/responder",
        json={"aprovado": True, "observacoes_cliente": "Aprovado!"},
    )

    # 6. Mecânico finaliza a manutenção (EM_EXECUCAO -> FINALIZADA)
    res_fin = await async_client.post(
        f"/ordens-servico/{os_id}/finalizar",
        json={
            "observacoes_mecanico": "Substituição realizada com sucesso, carro testado em rua de paralelepípedo."
        },
        headers=headers_meca,
    )
    assert res_fin.status_code == status.HTTP_200_OK

    # 7. Recepção registra o fechamento do caixa e entrega final (FINALIZADA -> ENTREGUE)
    payload_caixa = {
        "forma_pagamento": "PIX",
        "comprovante_transacao": "TX-999333222111",
    }
    response = await async_client.post(
        f"/ordens-servico/{os_id}/entregar", json=payload_caixa, headers=headers_recep
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "ENTREGUE"
    assert body["forma_pagamento"] == "PIX"
    assert body["comprovante_transacao"] == "TX-999333222111"
    assert body["data_conclusao"] is not None

    # Valida o cálculo matemático do faturamento consolidado
    # Serviços: 400.00. Peças: 650.00. Total: 1050.00
    assert body["valor_total_servicos"] == "400.00"
    assert body["valor_total_pecas"] == "650.00"
    assert body["valor_total_os"] == "1050.00"


@pytest.mark.asyncio
async def test_nao_deve_permitir_entrega_se_os_nao_estiver_finalizada(
    async_client: AsyncClient, token_recepcionista: str, db: AsyncSession
):
    """
    Cenário: Recepcionista tenta entregar veículo de uma OS que ainda está em diagnóstico.
    Resultado esperado: 400 Bad Request (Integridade de FSM mantida).
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    uid = str(uuid7())[:6]
    await garantir_usuario_existe_no_banco(
        token_recepcionista, "RECEPCIONISTA", db, uid
    )

    # Abre a OS
    res_os = await async_client.post(
        "/ordens-servico",
        json={
            "cliente_id": str(
                uuid7()
            ),  # ID fake apenas para falhar de forma rápida se não validado, ou usamos um ID válido
            "veiculo_id": str(uuid7()),
        },
        headers=headers,
    )

    # Caso precise criar de verdade para passar do 404 de abertura e ir pro 400 de entrega:
    # Vamos usar um ID de OS randômico que simula OS no status RECEBIDA/EM_DIAGNOSTICO no banco
    # Mas como o handler busca primeiro por ID (404), vamos testar a rejeição de FSM com uma OS existente

    # Criamos um cliente e veículo
    res_cli = await async_client.post(
        "/clientes",
        json={
            "nome": f"Marcos Fails {uid}",
            "email": f"marcos.fails.{uid}@gmail.com",
            "telefone": "11988887777",
            "cpf_cnpj": CPF().generate(),
            "tipo_pessoa": "FISICA",
        },
        headers=headers,
    )
    cliente_id = res_cli.json()["id"]

    res_vei = await async_client.post(
        "/veiculos",
        json={
            "placa": gerar_placa_valida_para_teste(),
            "marca": "Chevrolet",
            "modelo": "Onix",
            "ano": 2020,
            "cliente_id": cliente_id,
        },
        headers=headers,
    )
    veiculo_id = res_vei.json()["id"]

    # Abre OS (RECEBIDA -> EM_DIAGNOSTICO)
    res_os = await async_client.post(
        "/ordens-servico",
        json={"cliente_id": cliente_id, "veiculo_id": veiculo_id},
        headers=headers,
    )
    os_id = res_os.json()["id"]

    # Tenta entregar a OS que ainda está sob diagnóstico mecânico
    payload_caixa = {"forma_pagamento": "CREDITO", "quantidade_parcelas": 3}
    response = await async_client.post(
        f"/ordens-servico/{os_id}/entregar", json=payload_caixa, headers=headers
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Não é possível entregar veículo" in response.json()["detail"]


@pytest.mark.asyncio
async def test_mecanico_nao_deve_conseguir_registrar_entrega_rbac(
    async_client: AsyncClient, token_mecanico: str
):
    """
    Cenário: Mecânico tenta registrar o pagamento no caixa (violação de papéis).
    Resultado esperado: 403 Forbidden.
    """
    headers = {"Authorization": f"Bearer {token_mecanico}"}
    payload_caixa = {"forma_pagamento": "DINHEIRO"}
    response = await async_client.post(
        f"/ordens-servico/{uuid7()}/entregar", json=payload_caixa, headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
