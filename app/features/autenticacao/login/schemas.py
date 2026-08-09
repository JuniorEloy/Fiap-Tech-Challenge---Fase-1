from pydantic import BaseModel, Field, field_validator
from app.shared.domain.value_objects.email import Email


class LoginRequest(BaseModel):
    """Schema de entrada para o fluxo de autenticação."""
    email: str = Field(..., description="E-mail de acesso à conta")
    senha: str = Field(..., description="Senha secreta do operador")

    @field_validator("email")
    @classmethod
    def normalizar_e_validar_email(cls, valor: str) -> str:
        try:
            return Email(valor).valor
        except ValueError as exc:
            raise ValueError(str(exc))


class TokenResponse(BaseModel):
    """Schema de retorno contendo o Access Token e metadados de expiração."""
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int = Field(..., description="Tempo de vida do token em segundos")  