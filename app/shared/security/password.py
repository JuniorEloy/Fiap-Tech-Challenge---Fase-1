from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)


def gerar_hash_senha(senha_pura: str) -> str:
    return pwd_context.hash(senha_pura)


def verificar_senha(senha_pura: str, senha: str) -> bool:
    return pwd_context.verify(senha_pura, senha)
