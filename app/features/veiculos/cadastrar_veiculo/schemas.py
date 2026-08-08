from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from app.shared.domain.value_objects.placa import Placa


class CadastrarVeiculoRequest(BaseModel):
    placa: str = Field(
        ..., description="Placa do veículo (Formato tradicional ou Mercosul)"
    )
    marca: str = Field(
        ..., min_length=2, max_length=50, description="Marca (ex: Chevrolet)"
    )
    modelo: str = Field(
        ..., min_length=2, max_length=50, description="Modelo (ex: Onix)"
    )
    ano: int = Field(..., description="Ano de fabricação do veículo")
    cliente_id: UUID = Field(..., description="ID do cliente proprietário")

    @field_validator("placa")
    @classmethod
    def validar_placa(cls, valor: str) -> str:
        try:
            return Placa(
                valor
            ).valor  # Higieniza e devolve o valor puro de 7 caracteres
        except ValueError as exc:
            raise ValueError(str(exc))

    @field_validator("ano")
    @classmethod
    def validar_ano(cls, valor: int) -> int:
        ano_atual = datetime.now().year
        if valor < 1900 or valor > ano_atual + 1:
            raise ValueError(f"Ano inválido. Deve estar entre 1900 e {ano_atual + 1}.")
        return valor


class VeiculoResponse(BaseModel):
    id: UUID
    placa: str
    marca: str
    modelo: str
    ano: int
    cliente_id: UUID

    class Config:
        from_attributes = True

    @field_validator("placa", mode="before")
    @classmethod
    def formatar_placa(cls, valor: str) -> str:
        return Placa(valor).formatada
