from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class VeiculoRelatorioDTO(BaseModel):
    """Estrutura analítica de dados do veículo."""

    id: UUID
    placa: str
    marca: str
    modelo: str
    nome_proprietario: str

    model_config = ConfigDict(from_attributes=True)


class ClienteRelatorioDTO(BaseModel):
    """Representação rica do cliente contendo seus veículos aninhados."""

    id: UUID
    nome: str
    email: str
    telefone: str
    cpf_cnpj: str
    total_veiculos: int
    veiculos: List[VeiculoRelatorioDTO] = []

    model_config = ConfigDict(from_attributes=True)


class RelatorioClienteVeiculoResponse(BaseModel):
    """DTO Principal de Resposta do Relatório de Gerência."""

    total_clientes: int
    total_veiculos: int
    clientes: List[ClienteRelatorioDTO]

    model_config = ConfigDict(from_attributes=True)
