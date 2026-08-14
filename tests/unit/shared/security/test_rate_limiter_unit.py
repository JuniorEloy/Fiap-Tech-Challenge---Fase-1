import pytest
from unittest.mock import patch
from fastapi import Request
from app.shared.security.rate_limiter import (
    get_real_ip,
    get_login_rate_limit_key,
    get_user_rate_limit_key,
)


def criar_requisicao_mock(headers: dict = None, cookies: dict = None, client_host: str = None) -> Request:
    """Helper para instanciar um Request do FastAPI de forma nativa e segura usando o escopo ASGI."""
    headers_list = []
    if headers:
        for k, v in headers.items():
            headers_list.append((k.lower().encode("latin1"), v.encode("latin1")))

    scope = {
        "type": "http",
        "headers": headers_list,
    }
    
    if client_host:
        scope["client"] = (client_host, 12345)
        
    req = Request(scope)
    if cookies:
        # Injeta cookies de forma manual no escopo da requisição
        req._cookies = cookies
    return req


# =============================================================================
# TESTES DO PROVEDOR DE IP REAL (get_real_ip)
# =============================================================================

def test_get_real_ip_com_x_forwarded_for_multiplo():
    """
    Cenário: Requisição passa por proxies e apresenta múltiplos IPs no X-Forwarded-For.
    Resultado esperado: Deve extrair estritamente o primeiro IP da cadeia (IP do cliente original) e limpá-lo.
    """
    req = criar_requisicao_mock(headers={"X-Forwarded-For": "203.0.113.195, 70.41.3.18, 150.172.238.178"})
    ip = get_real_ip(req)
    assert ip == "203.0.113.195"


def test_get_real_ip_com_x_real_ip():
    """
    Cenário: Requisição apresenta o cabeçalho X-Real-IP padrão de proxies.
    Resultado esperado: Deve extrair e retornar o IP contido no cabeçalho de forma limpa.
    """
    req = criar_requisicao_mock(headers={"X-Real-IP": " 198.51.100.42 "})
    ip = get_real_ip(req)
    assert ip == "198.51.100.42"


def test_get_real_ip_fallback_client_host():
    """
    Cenário: Requisição direta sem cabeçalhos de proxy.
    Resultado esperado: Retorna o IP direto da conexão do cliente (client.host).
    """
    req = criar_requisicao_mock(client_host="192.168.1.15")
    ip = get_real_ip(req)
    assert ip == "192.168.1.15"


def test_get_real_ip_fallback_total_localhost():
    """
    Cenário: Requisição sem informações de cliente no escopo (ex: chamadas internas).
    Resultado esperado: Retorna o IP de loopback padrão (127.0.0.1).
    """
    req = Request(scope={"type": "http", "headers": []})
    ip = get_real_ip(req)
    assert ip == "127.0.0.1"


# =============================================================================
# TESTES DA CHAVE DE LOGIN (get_login_rate_limit_key)
# =============================================================================

def test_get_login_rate_limit_key_deve_retornar_ip_real():
    """
    Cenário: Solicitação de chave de limite para rota de login.
    Resultado esperado: Retorna o IP real do cliente.
    """
    req = criar_requisicao_mock(headers={"X-Real-IP": "177.42.18.99"})
    chave = get_login_rate_limit_key(req)
    assert chave == "177.42.18.99"


# =============================================================================
# TESTES DA CHAVE DE USUÁRIO / SESSÃO (get_user_rate_limit_key)
# =============================================================================

@patch("app.shared.security.rate_limiter.decodificar_token")
def test_get_user_rate_limit_key_com_token_bearer_valido(mock_decodificar):
    """
    Cenário: Usuário autenticado faz requisição enviando Token Bearer no cabeçalho Authorization.
    Resultado esperado: Retorna chave personalizada contendo o UUID do usuário (user:{sub}).
    """
    mock_decodificar.return_value = {"sub": "018f3a5b-7c10-7000-8000-000000000001", "role": "GERENTE"}
    req = criar_requisicao_mock(headers={"Authorization": "Bearer token_jwt_valido"})
    
    chave = get_user_rate_limit_key(req)
    assert chave == "user:018f3a5b-7c10-7000-8000-000000000001"
    mock_decodificar.assert_called_once_with("token_jwt_valido")


@patch("app.shared.security.rate_limiter.decodificar_token")
def test_get_user_rate_limit_key_com_token_bearer_sem_sub(mock_decodificar):
    """
    Cenário: Token Bearer decodifica mas não possui a claim 'sub'.
    Resultado esperado: Ignora o token e cai no fallback de IP (ip:{ip_real}).
    """
    mock_decodificar.return_value = {"role": "VISITANTE"}  # Sem "sub"
    req = criar_requisicao_mock(
        headers={"Authorization": "Bearer token_incompleto"},
        client_host="10.0.0.5"
    )
    
    chave = get_user_rate_limit_key(req)
    assert chave == "ip:10.0.0.5"


def test_get_user_rate_limit_key_com_cookie_refresh():
    """
    Cenário: Requisição sem token de acesso mas com Cookie de Refresh Token presente.
    Resultado esperado: Retorna chave baseada nos primeiros 16 caracteres do token de refresh (refresh_cookie:{prefixo}).
    """
    refresh_token_fake = "abcdefghijklmnopqrstuvwxyz1234567890"
    req = criar_requisicao_mock(
        cookies={"refresh_token": refresh_token_fake},
        client_host="10.0.0.10"
    )
    
    chave = get_user_rate_limit_key(req)
    assert chave == "refresh_cookie:abcdefghijklmnop"  # Cortado em 16 caracteres


def test_get_user_rate_limit_key_fallback_total_sem_credenciais():
    """
    Cenário: Requisição anônima sem cabeçalho Authorization e sem Cookie de Refresh.
    Resultado esperado: Retorna o fallback para IP real do cliente (ip:{ip_real}).
    """
    req = criar_requisicao_mock(client_host="189.50.32.12")
    chave = get_user_rate_limit_key(req)
    assert chave == "ip:189.50.32.12"
