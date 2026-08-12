from uuid import uuid7

import pytest
import pytest_asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
)

from app.main import app

from app.shared.infra.db.database import get_db

from app.features.usuarios.models import Usuario

from app.shared.security.roles import Role
from app.shared.security.password import gerar_hash_senha
from app.shared.security.tokens import criar_access_token
from app.features.usuarios.models import Usuario
from uuid import UUID

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/fiap_test"


# ==============================================================================
# DATABASE
# ==============================================================================


@pytest_asyncio.fixture
async def db_engine():

    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db(db_engine):

    async with db_engine.connect() as connection:
        # Inicia a transação principal do teste
        transaction = await connection.begin()

        # Inicia um SAVEPOINT (transação aninhada)
        nested = await connection.begin_nested()

        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
        )

        # Ouve o evento de término de transação do SQLAlchemy para recriar o SAVEPOINT
        # caso a aplicação faça um `await db.commit()` no meio do teste.
        @event.listens_for(session.sync_session, "after_transaction_end")
        def end_savepoint(session, transaction):
            nonlocal nested
            if not nested.is_active:
                nested = connection.sync_connection.begin_nested()

        yield session

        await session.close()

        # O rollback no final do teste sempre volta para o estado inicial,
        # ignorando qualquer commit que a aplicação tenha feito (graças ao SAVEPOINT).
        await transaction.rollback()


@pytest_asyncio.fixture(autouse=True)
async def override_db_dependency(db):

    async def override():
        yield db

    app.dependency_overrides[get_db] = override

    yield

    app.dependency_overrides.clear()


# ==============================================================================
# CLIENT
# ==============================================================================


@pytest_asyncio.fixture
async def async_client():

    transport = ASGITransport(
        app=app,
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver.local",
    ) as client:
        yield client


# ==============================================================================
# USERS
# ==============================================================================


async def criar_usuario(
    db: AsyncSession,
    role: Role,
    email: str,
    nome: str,
):

    usuario = Usuario(
        id=uuid7(),
        nome=nome,
        email=email,
        senha=gerar_hash_senha("SenhaSegura123!"),
        role=role,
        ativo=True,
    )

    db.add(usuario)

    await db.flush()

    return usuario


@pytest_asyncio.fixture
async def usuario_gerente(db):

    return await criar_usuario(
        db,
        Role.GERENTE,
        f"gerente-{uuid7()}@oficina.com",
        "Gerente Teste",
    )


@pytest_asyncio.fixture
async def usuario_recepcionista(db):

    return await criar_usuario(
        db,
        Role.RECEPCIONISTA,
        "recepcionista@oficina.com",
        "Recepcionista Teste",
    )


@pytest_asyncio.fixture
async def usuario_mecanico(db):

    return await criar_usuario(
        db,
        Role.MECANICO,
        "mecanico@oficina.com",
        "Mecanico Teste",
    )


@pytest_asyncio.fixture
async def usuario_estoquista(db):

    return await criar_usuario(
        db,
        Role.ESTOQUISTA,
        "estoquista@oficina.com",
        "Estoquista Teste",
    )


@pytest_asyncio.fixture
async def usuario_cliente(db):

    return await criar_usuario(
        db,
        Role.CLIENTE,
        "cliente@oficina.com",
        "Cliente Teste",
    )


# ==============================================================================
# TOKENS
# ==============================================================================


from uuid import UUID
import pytest
from app.shared.security.tokens import criar_access_token
from sqlalchemy import text

# UUID fixo para o Gerente de testes (compartilhado e reutilizado instantaneamente)
GERENTE_TESTE_ID = UUID("019ff420-0000-7000-8000-000000000001")


@pytest.fixture
async def token_gerente(db):
    """
    Gera o token e garante que o usuário gerente fixo existe no banco
    de forma ultra-rápida, sem criar lixo ou lentidão.
    """
    usuario = await db.get(Usuario, GERENTE_TESTE_ID)
    if not usuario:
        usuario = Usuario(
            id=GERENTE_TESTE_ID,
            nome="Gerente de Teste",
            email="gerente.teste@oficina.com",
            senha="hash_falso_ou_valido",
            role=Role.GERENTE,
            ativo=True,
        )
        db.add(usuario)
        await db.commit()

    return criar_access_token(usuario_id=GERENTE_TESTE_ID, role=Role.GERENTE)


# UUID fixo para a Recepcionista de testes
RECEPCIONISTA_TESTE_ID = UUID("019ff420-0000-7000-8000-000000000002")


@pytest.fixture
async def token_recepcionista(db):
    """
    Gera o token e garante que o usuário recepcionista fixo existe no banco
    de forma ultra-rápida, sem criar lixo ou lentidão.
    """
    usuario = await db.get(Usuario, RECEPCIONISTA_TESTE_ID)
    if not usuario:
        usuario = Usuario(
            id=RECEPCIONISTA_TESTE_ID,
            nome="Recepcionista de Teste",
            email="recepcao.teste@oficina.com",
            senha="hash_falso_ou_valido",
            role=Role.RECEPCIONISTA,
            ativo=True,
        )
        db.add(usuario)
        await db.commit()

    return criar_access_token(
        usuario_id=RECEPCIONISTA_TESTE_ID, role=Role.RECEPCIONISTA
    )


# UUID fixo para o Mecânico de testes
MECANICO_TESTE_ID = UUID("019ff420-0000-7000-8000-000000000003")


@pytest.fixture
async def token_mecanico(db):
    """
    Gera o token e garante que o usuário mecânico fixo existe no banco
    de forma ultra-rápida, sem criar lixo ou lentidão.
    """
    usuario = await db.get(Usuario, MECANICO_TESTE_ID)

    if not usuario:
        usuario = Usuario(
            id=MECANICO_TESTE_ID,
            nome="Mecânico de Teste",
            email="mecanico.teste@oficina.com",
            senha="hash_falso_ou_valido",
            role=Role.MECANICO,
            ativo=True,
        )
        db.add(usuario)
        await db.commit()

    return criar_access_token(
        usuario_id=MECANICO_TESTE_ID,
        role=Role.MECANICO,
    )


# UUID fixo para o Estoquista de testes
ESTOQUISTA_TESTE_ID = UUID("019ff420-0000-7000-8000-000000000004")


@pytest.fixture
async def token_estoquista(db):
    """
    Gera o token e garante que o usuário estoquista fixo existe no banco
    de forma ultra-rápida, sem criar lixo ou lentidão.
    """
    usuario = await db.get(Usuario, ESTOQUISTA_TESTE_ID)

    if not usuario:
        usuario = Usuario(
            id=ESTOQUISTA_TESTE_ID,
            nome="Estoquista de Teste",
            email="estoquista.teste@oficina.com",
            senha="hash_falso_ou_valido",
            role=Role.ESTOQUISTA,
            ativo=True,
        )
        db.add(usuario)
        await db.commit()

    return criar_access_token(
        usuario_id=ESTOQUISTA_TESTE_ID,
        role=Role.ESTOQUISTA,
    )


# UUID fixo para o Cliente de testes
CLIENTE_TESTE_ID = UUID("019ff420-0000-7000-8000-000000000005")


@pytest.fixture
async def token_cliente(db):
    """
    Gera o token e garante que o usuário cliente fixo existe no banco
    de forma ultra-rápida, sem criar lixo ou lentidão.
    """
    usuario = await db.get(Usuario, CLIENTE_TESTE_ID)

    if not usuario:
        usuario = Usuario(
            id=CLIENTE_TESTE_ID,
            nome="Cliente de Teste",
            email="cliente.teste@oficina.com",
            senha="hash_falso_ou_valido",
            role=Role.CLIENTE,
            ativo=True,
        )
        db.add(usuario)
        await db.commit()

    return criar_access_token(
        usuario_id=CLIENTE_TESTE_ID,
        role=Role.CLIENTE,
    )
