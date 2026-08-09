from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.features.clientes.models import TipoPessoa
from app.shared.domain.value_objects.cpf_cnpj import CpfCnpj
from app.shared.domain.value_objects.email import Email
from app.shared.domain.value_objects.telefone import Telefone


class EditarClienteRequest(BaseModel):
    """Schema de entrada para editar os dados do cliente (todos os campos opcionais)."""

    nome: Optional[str] = Field(
        None, min_length=3, max_length=150, description="Nome completo ou Razão Social"
    )
    email: Optional[EmailStr] = Field(None, description="Novo e-mail de contato")
    telefone: Optional[str] = Field(
        None,
        min_length=10,
        max_length=11,
        description="Telefone com DDD (apenas números)",
    )
    cpf_cnpj: Optional[str] = Field(
        None, description="CPF ou CNPJ para correção cadastral"
    )
    tipo_pessoa: Optional[TipoPessoa] = Field(None)

    @field_validator("cpf_cnpj")
    @classmethod
    def validar_documento(cls, valor: Optional[str]) -> Optional[str]:
        """Garante que o CPF/CNPJ, se fornecido, é conceitualmente válido."""
        if valor is None:
            return None
        try:
            vo = CpfCnpj(valor)
            return vo.valor  # Retorna limpo para persistência
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


class ClienteEditadoResponse(BaseModel):
    """Schema de saída do cliente atualizado com formatação rica."""

    id: UUID
    nome: str
    email: EmailStr
    telefone: str
    cpf_cnpj: str
    tipo_pessoa: TipoPessoa

    class Config:
        from_attributes = True

    @field_validator("cpf_cnpj", mode="before")
    @classmethod
    def formatar_documento(cls, valor: str) -> str:
        return CpfCnpj(valor).formatado

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
