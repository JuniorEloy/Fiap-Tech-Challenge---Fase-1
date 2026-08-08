import pytest
from datetime import timedelta
from uuid import uuid7

from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.autenticacao.models import RefreshTokenSession
from app.features.usuarios.models import Usuario
from app.shared.security.roles import Role
from app.shared.security.password import gerar_hash_senha
from app.shared.security.tokens import gerar_hash_token
from app.shared.utils.clock import DateTimeProvider


@pytest.mark.asyncio
async def test_login_com_credenciais_validas_deve_retornar_tokens(
    async_client: AsyncClient,
    usuario_gerente: Usuario,
):
    payload = {
        "email": usuario_gerente.email,
        "senha": "SenhaSegura123!",
    }

    response = await async_client.post("/auth/login", json=payload)

    assert response.status_code == status.HTTP_200_OK

    body = response.json()

    assert "access_token" in body
    assert body["token_type"].lower() == "bearer"
    assert "expires_in_seconds" in body
    assert "refresh_token" in response.cookies

    cookie = response.headers["set-cookie"]

    assert "httponly" in cookie.lower()
    assert "samesite=lax" in cookie.lower()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "credenciais",
    [
        {
            "email": "gerente@oficina.com",
            "senha": "SenhaIncorreta!",
        },
        {
            "email": "usuario@naoexiste.com",
            "senha": "SenhaSegura123!",
        },
    ],
)
async def test_login_com_credenciais_invalidas_deve_retornar_401(
    async_client: AsyncClient,
    credenciais: dict,
):
    response = await async_client.post(
        "/auth/login",
        json=credenciais,
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_refresh_token_sem_cookie_deve_retornar_401(
    async_client: AsyncClient,
):
    async_client.cookies.clear()

    response = await async_client.post("/auth/refresh")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_refresh_token_com_cookie_invalido_deve_retornar_401(
    async_client: AsyncClient,
):
    async_client.cookies.clear()

    async_client.cookies.set(
        "refresh_token",
        "token_invalido",
    )

    response = await async_client.post("/auth/refresh")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_refresh_token_expirado_deve_retornar_401(
    async_client: AsyncClient,
    db: AsyncSession,
):
    usuario = Usuario(
        id=uuid7(),
        nome="Usuario Expirado",
        email="expirado@oficina.com",
        senha=gerar_hash_senha("SenhaSegura123!"),
        role=Role.GERENTE,
        ativo=True,
    )

    token = "token_expirado"

    agora = DateTimeProvider().agora()

    sessao = RefreshTokenSession(
        id=uuid7(),
        usuario_id=usuario.id,
        token_hash=gerar_hash_token(token),
        expira_em=agora - timedelta(hours=1),
        created_at=agora - timedelta(hours=2),
    )

    db.add_all([usuario, sessao])
    await db.flush()

    async_client.cookies.set(
        "refresh_token",
        token,
    )

    response = await async_client.post("/auth/refresh")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_refresh_token_usuario_inativo_deve_retornar_401(
    async_client: AsyncClient,
    db: AsyncSession,
):
    usuario = Usuario(
        id=uuid7(),
        nome="Usuario Inativo",
        email="inativo@oficina.com",
        senha=gerar_hash_senha("SenhaSegura123!"),
        role=Role.GERENTE,
        ativo=False,
    )

    token = "token_usuario_inativo"

    agora = DateTimeProvider().agora()

    sessao = RefreshTokenSession(
        id=uuid7(),
        usuario_id=usuario.id,
        token_hash=gerar_hash_token(token),
        expira_em=agora + timedelta(hours=8),
        created_at=agora,
    )

    db.add_all([usuario, sessao])
    await db.flush()

    async_client.cookies.set(
        "refresh_token",
        token,
    )

    response = await async_client.post("/auth/refresh")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_logout_com_usuario_autenticado_deve_encerrar_sessao(
    async_client: AsyncClient,
    token_gerente: str,
):
    response = await async_client.post(
        "/auth/logout",
        headers={
            "Authorization": f"Bearer {token_gerente}",
        },
    )

    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_204_NO_CONTENT,
    ]


@pytest.mark.asyncio
async def test_logout_sem_token_deve_retornar_401(
    async_client: AsyncClient,
):
    response = await async_client.post("/auth/logout")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_reuso_de_token_revogado_fora_da_janela_de_graca_deve_invalidar_sessoes(
    async_client: AsyncClient,
    db: AsyncSession,
):
    usuario = Usuario(
        id=uuid7(),
        nome="Usuario Ataque",
        email="ataque@oficina.com",
        senha=gerar_hash_senha("SenhaSegura123!"),
        role=Role.GERENTE,
        ativo=True,
    )

    agora = DateTimeProvider().agora()

    token_comprometido = "token_comprometido"
    token_legitimo = "token_legitimo"

    sessao_comprometida = RefreshTokenSession(
        id=uuid7(),
        usuario_id=usuario.id,
        token_hash=gerar_hash_token(token_comprometido),
        revogado=True,
        created_at=agora - timedelta(seconds=15),
        expira_em=agora + timedelta(hours=8),
    )

    sessao_legitima = RefreshTokenSession(
        id=uuid7(),
        usuario_id=usuario.id,
        token_hash=gerar_hash_token(token_legitimo),
        revogado=False,
        created_at=agora,
        expira_em=agora + timedelta(hours=8),
    )

    db.add_all(
        [
            usuario,
            sessao_comprometida,
            sessao_legitima,
        ]
    )

    await db.flush()

    async_client.cookies.set(
        "refresh_token",
        token_comprometido,
    )

    response = await async_client.post("/auth/refresh")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    detail = response.json()["detail"].lower()

    assert "reuso" in detail or "violação" in detail

    await db.refresh(sessao_legitima)

    assert sessao_legitima.revogado is True


@pytest.mark.asyncio
async def test_reuso_de_token_revogado_dentro_da_janela_nao_revoga_sessoes(
    async_client: AsyncClient,
    db: AsyncSession,
):
    usuario = Usuario(
        id=uuid7(),
        nome="Usuario Janela",
        email="janela@oficina.com",
        senha=gerar_hash_senha("SenhaSegura123!"),
        role=Role.GERENTE,
        ativo=True,
    )

    agora = DateTimeProvider().agora()

    token_recente = "token_recente"
    token_ativo = "token_ativo"

    sessao_recente = RefreshTokenSession(
        id=uuid7(),
        usuario_id=usuario.id,
        token_hash=gerar_hash_token(token_recente),
        revogado=True,
        created_at=agora - timedelta(seconds=5),
        expira_em=agora + timedelta(hours=8),
    )

    sessao_ativa = RefreshTokenSession(
        id=uuid7(),
        usuario_id=usuario.id,
        token_hash=gerar_hash_token(token_ativo),
        revogado=False,
        created_at=agora,
        expira_em=agora + timedelta(hours=8),
    )

    db.add_all(
        [
            usuario,
            sessao_recente,
            sessao_ativa,
        ]
    )

    await db.flush()

    async_client.cookies.set(
        "refresh_token",
        token_recente,
    )

    response = await async_client.post("/auth/refresh")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    await db.refresh(sessao_ativa)

    assert sessao_ativa.revogado is False


@pytest.mark.asyncio
async def test_login_excedendo_rate_limit_deve_bloquear(
    async_client: AsyncClient,
):
    payload = {
        "email": "bruteforce@oficina.com",
        "senha": "SenhaErrada123!",
    }

    responses = []

    for _ in range(12):
        response = await async_client.post(
            "/auth/login",
            json=payload,
        )

        responses.append(response.status_code)

    assert status.HTTP_429_TOO_MANY_REQUESTS in responses
