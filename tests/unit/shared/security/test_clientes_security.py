import pytest

import pytest_asyncio
from uuid6 import uuid7

from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.shared.utils.clock import DateTimeProvider

from app.features.autenticacao.models import RefreshTokenSession

from app.shared.security.roles import Role
from app.shared.security.tokens import criar_access_token, gerar_hash_token
from datetime import timedelta


ENDPOINT = "/clientes"


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def token_por_role():

    async def criar(
        role: Role,
        usuario_id=None,
    ):
        if usuario_id is None:
            usuario_id = uuid7()

        return criar_access_token(
            usuario_id=usuario_id,
            role=role,
        )

    return criar


# ==============================================================================
# GET /clientes
# Listagem geral - somente GERENTE
# ==============================================================================


@pytest.mark.asyncio
async def test_listar_clientes_como_gerente_deve_retornar_200(
    async_client: AsyncClient,
    token_gerente: str,
):

    response = await async_client.get(
        ENDPOINT,
        headers=auth_header(token_gerente),
    )

    assert response.status_code == status.HTTP_200_OK

    assert response.headers["content-type"].startswith("application/json")

    body = response.json()

    assert isinstance(body, list)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        Role.RECEPCIONISTA,
        Role.MECANICO,
        Role.ESTOQUISTA,
        Role.CLIENTE,
    ],
)
async def test_listar_clientes_com_roles_nao_autorizadas_deve_retornar_403(
    async_client: AsyncClient,
    role: Role,
):

    token = criar_access_token(
        usuario_id=uuid7(),
        role=role,
    )

    response = await async_client.get(
        ENDPOINT,
        headers=auth_header(token),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    body = response.json()

    assert "detail" in body

    assert "permissão" in body["detail"].lower()


@pytest.mark.asyncio
async def test_listar_clientes_sem_token_deve_retornar_401(
    async_client: AsyncClient,
):

    response = await async_client.get(ENDPOINT)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "authorization",
    [
        "Bearer token_invalido",
        "Basic abc123",
        "Bearer",
        "Bearer ",
        "123456",
    ],
)
async def test_listar_clientes_com_authorization_invalido_deve_retornar_401(
    async_client: AsyncClient,
    authorization: str,
):

    response = await async_client.get(
        ENDPOINT,
        headers={"Authorization": authorization},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_post_em_endpoint_get_deve_retornar_405(
    async_client: AsyncClient,
    token_gerente: str,
):

    response = await async_client.post(
        ENDPOINT,
        headers=auth_header(token_gerente),
    )

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# ==============================================================================
# GET /clientes/documento/{documento}
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        Role.GERENTE,
        Role.RECEPCIONISTA,
    ],
)
async def test_buscar_cliente_por_documento_com_roles_autorizadas_deve_permitir(
    async_client: AsyncClient,
    role: Role,
):

    token = criar_access_token(
        usuario_id=uuid7(),
        role=role,
    )

    response = await async_client.get(
        "/clientes/documento/52998224725",
        headers=auth_header(token),
    )

    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_404_NOT_FOUND,
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        Role.MECANICO,
        Role.ESTOQUISTA,
        Role.CLIENTE,
    ],
)
async def test_buscar_cliente_por_documento_com_roles_nao_autorizadas_deve_retornar_403(
    async_client: AsyncClient,
    role: Role,
):

    token = criar_access_token(
        usuario_id=uuid7(),
        role=role,
    )

    response = await async_client.get(
        "/clientes/documento/52998224725",
        headers=auth_header(token),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    body = response.json()

    assert "detail" in body

    assert "permissão" in body["detail"].lower()


# ==============================================================================
# 2. TESTES: GET /clientes/documento/{documento}
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        Role.GERENTE,
        Role.RECEPCIONISTA,
    ],
)
async def test_buscar_cliente_por_documento_com_roles_autorizadas_deve_permitir(
    async_client: AsyncClient,
    token_por_role,
    role: Role,
):
    """
    Cenário:
    - Gerente ou Recepcionista pesquisando cliente por documento.

    Resultado esperado:
    - 200 OK ou 404 Not Found
    - RBAC permite acesso.
    """

    token = await token_por_role(role)

    response = await async_client.get(
        "/clientes/documento/52998224725",
        headers=auth_header(token),
    )

    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_404_NOT_FOUND,
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        Role.MECANICO,
        Role.ESTOQUISTA,
        Role.CLIENTE,
    ],
)
async def test_buscar_cliente_por_documento_com_roles_nao_autorizadas_deve_retornar_403(
    async_client: AsyncClient,
    token_por_role,
    role: Role,
):
    """
    Cenário:
    Usuário sem permissão consulta cliente por documento.

    Resultado esperado:
    - 403 Forbidden
    """

    token = await token_por_role(role)

    response = await async_client.get(
        "/clientes/documento/52998224725",
        headers=auth_header(token),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    body = response.json()

    assert "detail" in body
    assert "permissão" in body["detail"].lower()


# ==============================================================================
# 3. TESTES: GET /clientes/{cliente_id}
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        Role.GERENTE,
        Role.RECEPCIONISTA,
    ],
)
async def test_buscar_cliente_por_id_com_roles_administrativas_deve_permitir(
    async_client: AsyncClient,
    token_por_role,
    role: Role,
):
    """
    Cenário:
    Perfil administrativo acessando cliente.

    Resultado esperado:
    - 200 OK
    - ou 404 caso cliente não exista.
    """

    token = await token_por_role(role)

    response = await async_client.get(
        f"/clientes/{uuid7()}",
        headers=auth_header(token),
    )

    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_404_NOT_FOUND,
    ]


@pytest.mark.asyncio
async def test_cliente_acessando_proprio_id_deve_permitir(
    async_client: AsyncClient,
    token_por_role,
):
    """
    Cenário:
    Cliente acessa seu próprio cadastro.
    """

    cliente_id = uuid7()

    token = await token_por_role(
        Role.CLIENTE,
        usuario_id=cliente_id,
    )

    response = await async_client.get(
        f"/clientes/{cliente_id}",
        headers=auth_header(token),
    )

    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_404_NOT_FOUND,
    ]


@pytest.mark.asyncio
async def test_cliente_acessando_outro_id_deve_retornar_403(
    async_client: AsyncClient,
    token_por_role,
):
    """
    Cenário:
    Cliente tenta acessar cadastro de outro cliente.

    Resultado esperado:
    - 403 Forbidden
    """

    cliente_a = uuid7()
    cliente_b = uuid7()

    token = await token_por_role(
        Role.CLIENTE,
        usuario_id=cliente_a,
    )

    response = await async_client.get(
        f"/clientes/{cliente_b}",
        headers=auth_header(token),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    body = response.json()

    assert "detail" in body
    assert (
        "permissão" in body["detail"].lower()
        or "outro usuário" in body["detail"].lower()
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        Role.MECANICO,
        Role.ESTOQUISTA,
    ],
)
async def test_buscar_cliente_por_id_com_roles_bloqueadas_deve_retornar_403(
    async_client: AsyncClient,
    token_por_role,
    role: Role,
):
    """
    Cenário:
    Mecânico e Estoquista tentando acessar dados de clientes.

    Resultado esperado:
    - 403 Forbidden
    """

    token = await token_por_role(role)

    response = await async_client.get(
        f"/clientes/{uuid7()}",
        headers=auth_header(token),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    body = response.json()

    assert "detail" in body
    assert "permissão" in body["detail"].lower()
