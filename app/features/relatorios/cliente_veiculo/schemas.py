from uuid import UUID
from typing import List
from pydantic import BaseModel


class ClienteResumoDTO(BaseModel):
    id: UUID
    nome: str
    email: str
    cpf_cnpj: str
    total_veiculos: int


class VeiculoResumoDTO(BaseModel):
    id: UUID
    placa: str
    marca: str
    modelo: str
    nome_proprietario: str


class DashboardGeralResponse(BaseModel):
    total_clientes: int
    total_veiculos: int
    clientes: List[ClienteResumoDTO]
    veiculos: List[VeiculoResumoDTO]
