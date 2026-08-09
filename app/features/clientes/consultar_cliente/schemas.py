from uuid import UUID
from pydantic import BaseModel, field_validator, ConfigDict, EmailStr, Field
from app.shared.domain.value_objects.cpf_cnpj import CpfCnpj
from app.features.clientes.models import TipoPessoa
from app.shared.domain.value_objects.email import Email
from app.shared.domain.value_objects.telefone import Telefone


class ClienteResponse(BaseModel):
    id: UUID
    nome: str
    email: EmailStr
    cpf_cnpj: str
    telefone: str
    tipo_pessoa: TipoPessoa

    @field_validator("cpf_cnpj")
    @classmethod
    def validar_documento(cls, v: str) -> str:
        # Instanciar o VO dispara as regras de validação automaticamente
        doc = CpfCnpj(v)
        return doc.valor  # Retorna apenas os dígitos limpos

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

    model_config = ConfigDict(from_attributes=True)
