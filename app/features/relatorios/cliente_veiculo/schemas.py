from uuid import UUID
from typing import List
from pydantic import BaseModel, Field


class ClienteRelatorioDTO(BaseModel):
    """Representação consolidada e formatada do cliente para fins de auditoria."""

    id: UUID
    nome: str
    email: str
    telefone: str = Field(
        ..., description="Telefone higienizado e formatado com DDD/máscara"
    )
    cpf_cnpj: str = Field(
        ..., description="Documento do cliente com máscara de pontuação"
    )
    total_veiculos: int

    class Config:
        from_attributes = True


class VeiculoRelatorioDTO(BaseModel):
    """Representação direta do veículo associado ao seu proprietário."""

    id: UUID
    placa: str = Field(
        ..., description="Placa higienizada e formatada no padrão Mercosul ou antigo"
    )
    marca: str
    modelo: str
    nome_proprietario: str

    class Config:
        from_attributes = True


class RelatorioClienteVeiculoResponse(BaseModel):
    """Resposta unificada do relatório de faturamento e frota da oficina."""

    total_clientes: int
    total_veiculos: int
    clientes: List[ClienteRelatorioDTO]
    veiculos: List[VeiculoRelatorioDTO]

    class Config:
        from_attributes = True
