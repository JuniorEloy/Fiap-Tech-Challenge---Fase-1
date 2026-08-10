from pydantic import BaseModel, Field, ConfigDict


class TokenResponse(BaseModel):
    """Schema de Saída: Novo par de credenciais de acesso temporário."""

    access_token: str = Field(
        ..., description="Novo JSON Web Token de acesso de curta duração"
    )
    token_type: str = Field(
        "bearer", description="Esquema de autenticação HTTP adotado"
    )
    expires_in_seconds: int = Field(
        900, description="Tempo de expiração do novo access token em segundos"
    )

    model_config = ConfigDict(from_attributes=True)
