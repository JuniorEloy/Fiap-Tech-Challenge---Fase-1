from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from app.shared.domain.value_objects.placa import Placa


class EditarVeiculoRequest(BaseModel):
    """Schema de entrada para atualizar parcialmente os dados de um veículo."""

    placa: Optional[str] = Field(
        None, description="Placa para correção cadastral (Tradicional ou Mercosul)"
    )
    marca: Optional[str] = Field(None, min_length=2, max_length=50)
    modelo: Optional[str] = Field(None, min_length=2, max_length=50)
    ano: Optional[int] = Field(None)
    cliente_id: Optional[UUID] = Field(
        None, description="Novo proprietário em caso de transferência"
    )

    @field_validator("placa")
    @classmethod
    def validar_placa(cls, valor: Optional[str]) -> Optional[str]:
        if valor is None:
            return None
        try:
            return Placa(valor).valor  # Devolve placa limpa de 7 caracteres
        except ValueError as exc:
            raise ValueError(str(exc))

    @field_validator("ano")
    @classmethod
    def validar_ano(cls, valor: Optional[int]) -> Optional[int]:
        if valor is None:
            return None
        ano_atual = datetime.now().year
        if valor < 1900 or valor > ano_atual + 1:
            raise ValueError(f"Ano inválido. Deve estar entre 1900 e {ano_atual + 1}.")
        return valor


class VeiculoEditadoResponse(BaseModel):
    """Schema de resposta unificado e formatado."""

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
