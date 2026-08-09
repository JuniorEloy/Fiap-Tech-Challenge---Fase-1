from typing import Optional
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class ServicoResponse(BaseModel):
    """Schema de Saída: Dados do serviço cadastrado no catálogo."""

    id: UUID
    nome: str
    descricao: Optional[str] = None
    preco_mao_de_obra: Decimal
    duracao_estimada_minutos: int
    ativo: bool

    model_config = ConfigDict(from_attributes=True)
