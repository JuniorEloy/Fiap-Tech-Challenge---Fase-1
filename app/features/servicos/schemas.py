from typing import Optional
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class ServicoResponse(BaseModel):
    """Schema de Saída: Confirmação rica do serviço inserido ou listado no catálogo."""

    id: UUID
    nome: str
    descricao: Optional[str] = None
    preco_mao_de_obra: Decimal
    duracao_estimada_minutos: int
    ativo: bool
    permite_servico_expresso: bool

    model_config = ConfigDict(from_attributes=True)
