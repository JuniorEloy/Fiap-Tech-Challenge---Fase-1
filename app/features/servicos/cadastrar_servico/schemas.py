from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


class CadastrarServicoRequest(BaseModel):
    """Schema de Entrada: Dados necessários para catalogar o serviço (mão de obra)."""

    nome: str = Field(
        ..., min_length=2, max_length=100, description="Nome identificador do serviço"
    )
    descricao: Optional[str] = Field(
        None, max_length=255, description="Descrição detalhada das etapas de execução"
    )
    preco_mao_de_obra: Decimal = Field(
        ..., gt=0, description="Preço sugerido cobrado pela mão de obra"
    )
    duracao_estimada_minutos: int = Field(
        30, gt=0, description="Duração estimada de execução em minutos"
    )
    permite_servico_expresso: bool = Field(False, description="Flag de fluxo expresso")

    @field_validator("preco_mao_de_obra")
    @classmethod
    def validar_preco_positivo(cls, valor: Decimal) -> Decimal:
        if valor <= Decimal("0.00"):
            raise ValueError(
                "O preço da mão de obra deve ser estritamente maior que zero."
            )
        return valor
