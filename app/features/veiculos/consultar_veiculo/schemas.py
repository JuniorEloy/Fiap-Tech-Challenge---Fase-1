from uuid import UUID
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.shared.domain.value_objects.placa import Placa


class ConsultarVeiculoResponse(BaseModel):
    id: UUID
    placa: str
    marca: str
    modelo: str
    ano: int
    cliente_id: UUID

    model_config = ConfigDict(from_attributes=True)

    # Reconstrói a Placa formatando a saída de acordo com o padrão do VO
    @field_validator("placa", mode="before")
    @classmethod
    def formatar_placa(cls, valor: str) -> str:
        return Placa(valor).formatada
