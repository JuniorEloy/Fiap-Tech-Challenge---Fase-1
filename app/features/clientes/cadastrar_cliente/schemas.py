from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.features.clientes.models import TipoPessoa
from app.shared.domain.value_objects.cpf_cnpj import CpfCnpj
from app.shared.domain.value_objects.email import Email
from app.shared.domain.value_objects.telefone import Telefone


class CadastrarClienteRequest(BaseModel):
    """Esquema de entrada para cadastrar cliente."""

    nome: str = Field(
        ..., min_length=3, max_length=150, description="Nome completo ou Razão Social"
    )
    email: EmailStr = Field(..., description="E-mail exclusivo de contato")
    telefone: str = Field(
        ...,
        min_length=10,
        max_length=11,
        description="Telefone com DDD (apenas números)",
    )
    cpf_cnpj: str = Field(..., description="CPF (11 dígitos) ou CNPJ (14 dígitos)")
    tipo_pessoa: TipoPessoa = Field(default=TipoPessoa.FISICA)

    @field_validator("cpf_cnpj")
    @classmethod
    def validar_documento(cls, valor: str) -> str:
        """Garante que o CPF/CNPJ é conceitualmente válido usando o VO rico."""
        try:
            # Tenta instanciar o VO; se disparar ValueError, o Pydantic captura
            vo = CpfCnpj(valor)
            return vo.valor  # Retorna o valor limpo e higienizado para persistência
        except ValueError as exc:
            raise ValueError(str(exc))

    @field_validator("email")
    @classmethod
    def validar_email(cls, v: str) -> str:
        # Usa o VO para validar a entrada e já higieniza (retorna limpo)
        return Email(v).valor

    @field_validator("telefone")
    @classmethod
    def validar_telefone(cls, v: str) -> str:
        # Usa o VO para validar e salvar apenas os dígitos limpos no banco
        return Telefone(v).valor


class ClienteResponse(BaseModel):
    """Esquema de saída do cliente cadastrado."""

    id: UUID
    nome: str
    email: EmailStr
    telefone: str
    cpf_cnpj: str
    tipo_pessoa: TipoPessoa

    class Config:
        from_attributes = True

    # Customização para que a resposta exiba o CPF/CNPJ formatado de forma legível
    @field_validator("cpf_cnpj", mode="before")
    @classmethod
    def formatar_documento(cls, valor: str) -> str:
        return CpfCnpj(valor).formatado

    @field_validator("telefone", mode="before")
    @classmethod
    def formatar_telefone(cls, v: str) -> str:
        # Retorna formatado no padrão (XX) XXXXX-XXXX
        return Telefone(v).formatado
