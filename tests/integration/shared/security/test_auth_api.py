import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid7

from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.features.autenticacao.models import RefreshTokenSession
from app.features.autenticacao.refresh.handler import RefreshHandler
from app.features.usuarios.models import Usuario
from app.shared.security.roles import Role
from app.shared.security.password import gerar_hash_senha
from app.shared.security.tokens import gerar_hash_token
from app.shared.utils.clock import DateTimeProvider

from app.shared.security.tokens import gerar_hash_token, decodificar_token


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

# 🌟 CORREÇÃO DO RATE LIMITER: 
# Em vez de desativar globalmente, desativamos dinamicamente para todos os testes,
# EXCETO para aqueles que validam explicitamente o rate limit (que possuem 'rate_limit' ou 'ratelimit' no nome).
@pytest.fixture(autouse=True)
def gerenciar_rate_limiter_nos_testes(request):
    try:
        from app.shared.security.rate_limiter import limiter
        if "rate_limit" in request.node.name or "ratelimit" in request.node.name:
            limiter.enabled = True  # Ativo para testes de rate limit
        else:
            limiter.enabled = False # Desativado para os demais para evitar 429
        yield
        limiter.enabled = True  # Restaura o estado padrão ao final
    except ImportError:
        yield


@pytest.mark.asyncio
async def test_logout_com_sucesso_deve_revogar_token_e_limpar_cookie(
    async_client: AsyncClient
):
    """
    Cenário: Operador válido faz login, obtém sessão e decide deslogar (Logout).
    Resultado esperado: 
    1. 200 OK no logout.
    2. Envio do cabeçalho Set-Cookie para expirar/deletar o cookie 'refresh_token'.
    3. Qualquer chamada subsequente de Refresh usando o token antigo deve falhar (401),
       provando que a sessão foi marcada de fato como revogada no banco de dados.
    """
    # 1. Faz login com o gerente para gerar uma sessão real de refresh token no banco
    login_payload = {
        "email": "armando.gerente@oficina.com",
        "senha": "Gerente123!"
    }
    login_res = await async_client.post("/auth/login", json=login_payload)
    assert login_res.status_code == status.HTTP_200_OK
    
    body_login = login_res.json()
    access_token = body_login.get("access_token")
    
    # Captura o cookie de refresh gerado no login
    refresh_cookie = login_res.cookies.get("refresh_token")
    assert refresh_cookie is not None

    # 2. Executa o Logout passando o cookie capturado e cabeçalho de autenticação
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    logout_res = await async_client.post(
        "/auth/logout",
        cookies={"refresh_token": refresh_cookie},
        headers=headers
    )
    assert logout_res.status_code == status.HTTP_200_OK

    # Verifica se o cabeçalho de resposta configurou a remoção do cookie
    novo_refresh_cookie = logout_res.cookies.get("refresh_token")
    assert novo_refresh_cookie in (None, "", "delete-cookie")

    # 3. PROVA DE SEGURANÇA: Tenta usar o refresh token antigo que acabou de ser deslogado
    refresh_res = await async_client.post(
        "/auth/refresh",
        cookies={"refresh_token": refresh_cookie}
    )
    assert refresh_res.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_logout_sem_cookie_deve_funcionar_de_forma_idempotente_autenticado(
    async_client: AsyncClient
):
    """
    Cenário: Usuário autenticado tenta efetuar logout mas não possui um cookie ativo
             (ex: cookie já expirou ou foi apagado pelo navegador).
    Resultado esperado: 200 OK (o logout deve ser idempotente para sessões autenticadas).
    """
    # 1. Faz login com o gerente para obter autenticação válida
    login_payload = {
        "email": "armando.gerente@oficina.com",
        "senha": "Gerente123!"
    }
    login_res = await async_client.post("/auth/login", json=login_payload)
    assert login_res.status_code == status.HTTP_200_OK
    
    access_token = login_res.json().get("access_token")
    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Executa o logout SEM enviar o cookie de refresh
    response = await async_client.post("/auth/logout", headers=headers)
    
    # Deve responder com 200 OK com sucesso, limpando de forma idempotente
    assert response.status_code == status.HTTP_200_OK
    
    cookie_limpo = response.cookies.get("refresh_token")
    assert cookie_limpo in (None, "", "delete-cookie")

@pytest.mark.asyncio
async def test_deve_renovar_token_com_sucesso_usando_cookie_httponly(
    async_client: AsyncClient
):
    """
    Cenário: Operador válido tenta renovar o token enviando o Cookie de Refresh Token.
    Resultado esperado: 200 OK, geração de novo access token e cookie de refresh rotacionado (RTR).
    """
    # 1. Faz login com operador da Seed para capturar os cookies reais
    login_payload = {
        "email": "armando.gerente@oficina.com",
        "senha": "Gerente123!"
    }
    login_res = await async_client.post("/auth/login", json=login_payload)
    assert login_res.status_code == status.HTTP_200_OK
    
    # Captura o cookie HttpOnly de refresh retornado no login
    refresh_cookie = login_res.cookies.get("refresh_token")
    assert refresh_cookie is not None

    # 2. Executa a chamada de renovação (refresh) enviando o cookie capturado
    response = await async_client.post(
        "/auth/refresh",
        cookies={"refresh_token": refresh_cookie}
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert isinstance(body["expires_in_seconds"], int)

    # 3. Garante que o mecanismo de Refresh Token Rotation (RTR) enviou um NOVO cookie
    novo_refresh_cookie = response.cookies.get("refresh_token")
    assert novo_refresh_cookie is not None
    assert novo_refresh_cookie != refresh_cookie  # O token DEVE ter rotacionado!


@pytest.mark.asyncio
async def test_refresh_sem_cookie_deve_retornar_401(async_client: AsyncClient):
    """
    Cenário: Chamada ao endpoint de refresh sem apresentar o cookie necessário.
    Resultado esperado: 401 Unauthorized com mensagem clara de erro.
    """
    response = await async_client.post("/auth/refresh")
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Cookie de Refresh Token não fornecido."


@pytest.mark.asyncio
async def test_refresh_com_cookie_invalido_deve_retornar_401(async_client: AsyncClient):
    """
    Cenário: Apresenta um cookie com assinatura ou hash adulterado/falso.
    Resultado esperado: 401 Unauthorized.
    """
    response = await async_client.post(
        "/auth/refresh",
        cookies={"refresh_token": "token_completamente_falso_sha256"}
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Sessão de refresh inválida, expirada ou revogada." in response.json()["detail"]


@pytest.mark.asyncio
async def test_politica_rtr_deve_impedir_uso_duplicado_do_mesmo_refresh_token(
    async_client: AsyncClient
):
    """
    Cenário: Um atacante tenta reutilizar um refresh token que já foi rotacionado (utilizado uma vez).
    Resultado esperado: 401 Unauthorized na segunda tentativa, impedindo sequestro de sessão.
    """
    # 1. Faz login inicial
    login_payload = {
        "email": "barbara.recepcao@oficina.com",
        "senha": "Recepcao123!"
    }
    login_res = await async_client.post("/auth/login", json=login_payload)
    assert login_res.status_code == status.HTTP_200_OK
    refresh_cookie = login_res.cookies.get("refresh_token")

    # 2. Primeira renovação: Deve ter sucesso absoluto (RTR invalida o token de entrada)
    res_1 = await async_client.post(
        "/auth/refresh",
        cookies={"refresh_token": refresh_cookie}
    )
    assert res_1.status_code == status.HTTP_200_OK

    # 3. Segunda tentativa com o MESMO token antigo: Deve falhar imediatamente!
    res_2 = await async_client.post(
        "/auth/refresh",
        cookies={"refresh_token": refresh_cookie}
    )
    assert res_2.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Sessão de refresh inválida, expirada ou revogada." in res_2.json()["detail"]


# =============================================================================
# 🎯 TESTES DIRETOS DO HANDLER (COBERTURA MÁXIMA DA GERAÇÃO DE NOVOS TOKENS/RTR)
# =============================================================================

@pytest.mark.asyncio
async def test_handler_refresh_sucesso_deve_persistir_e_rotacionar_corretamente(db):
    """
    Cenário: Executa o RefreshHandler diretamente para testar as linhas de sucesso,
             geração de novos tokens, atualização da sessão antiga para revogada,
             criação da nova sessão no banco de dados e retorno do DTO/Tupla de sucesso.
    """
    # 1. Cria um usuário de teste ativo no banco de dados para a sessão
    uid = uuid7()
    usuario_teste = Usuario(
        id=uid,
        nome="Mecanico de Teste Refresh",
        email=f"mecanico.refresh.{str(uid)[:6]}@oficina.com",
        senha=gerar_hash_senha("SenhaSegura123!"),
        role=Role.MECANICO,
        ativo=True
    )
    db.add(usuario_teste)
    await db.commit()

    # 2. Cria uma sessão activa no banco de dados para esse usuário
    raw_token_teste = "raw_refresh_token_teste_de_cobertura_12345"
    token_hash_original = gerar_hash_token(raw_token_teste)
    
    sessao_original = RefreshTokenSession(
        usuario_id=usuario_teste.id,
        token_hash=token_hash_original,
        expira_em=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=2),
        revogado=False
    )
    db.add(sessao_original)
    await db.commit()

    # 3. Instancia o Handler e executa a rotação de token de forma isolada
    handler = RefreshHandler(db)
    novo_access, novo_refresh_bruto, exp_segundos = await handler.executar(raw_token_teste)

    # 4. Asserções do retorno do Handler
    assert novo_access is not None
    assert novo_refresh_bruto is not None
    assert novo_refresh_bruto != raw_token_teste  # Deve ser um novo token gerado (RTR)
    assert isinstance(exp_segundos, int)
    assert exp_segundos > 0

    # 5. Asserções de Persistência no Banco de Dados (Verifica se as linhas foram cobertas fisicamente)
    # 5.1 A sessão antiga DEVE ter sido marcada como revogada
    await db.refresh(sessao_original)
    assert sessao_original.revogado is True

    # 5.2 Uma NOVA sessão ativa deve ter sido criada no banco com o hash do novo_refresh_bruto
    novo_hash_esperado = gerar_hash_token(novo_refresh_bruto)
    stmt = select(RefreshTokenSession).where(
        RefreshTokenSession.token_hash == novo_hash_esperado
    )
    res = await db.execute(stmt)
    nova_sessao_db = res.scalar_one_or_none()

    assert nova_sessao_db is not None
    assert nova_sessao_db.usuario_id == usuario_teste.id
    assert nova_sessao_db.revogado is False
    # Garante que a expiração foi salva no futuro (próximo de 8h)
    assert nova_sessao_db.expira_em > datetime.now(timezone.utc) + timedelta(hours=7)

    # 5.3 O access token gerado deve conter o payload de identificação correto do usuário e papel
    payload = decodificar_token(novo_access)
    assert payload["sub"] == str(usuario_teste.id)
    assert payload["role"] == Role.MECANICO
