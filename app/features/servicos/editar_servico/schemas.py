from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


class EditarServicoRequest(BaseModel):
    """Schema de Entrada: Permite atualização parcial das características de um serviço cadastrado."""

    nome: Optional[str] = Field(
        None, min_length=2, max_length=100, description="Nome identificador do serviço"
    )
    descricao: Optional[str] = Field(
        None, max_length=255, description="Descrição das etapas operacionais"
    )
    preco_mao_de_obra: Optional[Decimal] = Field(
        None, gt=0, description="Novo preço cobrado pela mão de obra"
    )
    duracao_estimada_minutos: Optional[int] = Field(
        None, gt=0, description="Nova duração de execução estimada em minutos"
    )
    ativo: Optional[bool] = Field(
        None, description="Status de ativação cadastral do serviço"
    )

    @field_validator("preco_mao_de_obra")
    @classmethod
    def validar_preco_positivo_se_fornecido(
        cls, valor: Optional[Decimal]
    ) -> Optional[Decimal]:
        """Garante que um novo preço proposto seja estritamente positivo."""
        if valor is not None and valor <= Decimal("0.00"):
            raise ValueError(
                "O preço da mão de obra atualizado deve ser maior que zero."
            )
        return valor
