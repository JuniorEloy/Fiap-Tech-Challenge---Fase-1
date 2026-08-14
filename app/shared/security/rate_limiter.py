from fastapi import Request
from slowapi import Limiter
from app.shared.security.tokens import decodificar_token


def get_real_ip(request: Request) -> str:
    """
    Captura o IP real do cliente, considerando que a aplicação pode estar
    atrás de um Nginx, Traefik, Cloudflare ou Load Balancer (NAT/Proxy).
    """
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        # O cabeçalho pode conter múltiplos IPs (ex: "client, proxy1, proxy2").
        # O primeiro IP é sempre o do cliente original.
        return x_forwarded_for.split(",")[0].strip()

    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip.strip()

    # Fallback para a conexão direta se não houver proxy
    return request.client.host if request.client else "127.0.0.1"


def get_login_rate_limit_key(request: Request) -> str:
    return get_real_ip(request)


def get_user_rate_limit_key(request: Request) -> str:
    """
    Chave para rotas autenticadas (como /refresh): usa o ID do usuário (sub) no JWT
    ou no Cookie de refresh. Se não estiver autenticado, usa o IP Real.
    """
    # 1. Tenta extrair do token de autorização Bearer
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        payload = decodificar_token(token)
        if payload and "sub" in payload:
            return f"user:{payload['sub']}"

    # 2. Tenta extrair do Cookie de Refresh Token
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        # Usa um pedaço do hash do token como chave única por sessão
        return f"refresh_cookie:{refresh_token[:16]}"

    # 3. Fallback para IP Real caso a requisição não tenha credencial
    return f"ip:{get_real_ip(request)}"


# Instância global do Limiter
limiter = Limiter(key_func=get_real_ip)
