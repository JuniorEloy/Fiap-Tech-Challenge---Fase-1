from uuid import UUID
from pydantic import BaseModel, field_validator, ConfigDict, EmailStr, Field
from app.shared.domain.value_objects.cpf_cnpj import CpfCnpj
from app.features.clientes.models import TipoPessoa


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

    model_config = ConfigDict(from_attributes=True)
