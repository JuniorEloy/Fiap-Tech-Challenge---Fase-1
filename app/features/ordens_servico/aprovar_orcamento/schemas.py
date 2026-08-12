from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, AliasPath
from app.features.ordens_servico.models import StatusOS


class ResponderOrcamentoRequest(BaseModel):
    """Schema de Entrada: Resposta do cliente para aprovação ou rejeição do orçamento."""

    aprovado: bool = Field(
        ...,
        description="Indica se o cliente aprovou (True) ou rejeitou (False) o orçamento.",
    )
    observacoes_cliente: Optional[str] = Field(
        None,
        max_length=255,
        description="Observações ou justificativas do cliente sobre a aprovação/rejeição.",
    )


class ItemServicoResponse(BaseModel):
    """Schema de Saída: Confirmação do serviço na resposta do orçamento."""

    servico_id: UUID = Field(validation_alias="servico_base_id")
    nome: str = Field(validation_alias=AliasPath("servico_base", "nome"))
    preco_aplicado: Decimal
    duracao_minutos: int

    model_config = ConfigDict(from_attributes=True)


class ItemPecaResponse(BaseModel):
    """Schema de Saída: Confirmação da peça utilizada na resposta do orçamento."""

    peca_id: UUID
    nome_peca: str = Field(validation_alias=AliasPath("peca", "nome"))
    quantidade: int
    preco_unitario_aplicado: Decimal

    model_config = ConfigDict(from_attributes=True)


class RespostaOrcamentoResponse(BaseModel):
    """Schema de Saída: Estado da Ordem de Serviço após resposta do cliente."""

    id: UUID
    cliente_id: UUID
    veiculo_id: UUID
    mecanico_id: Optional[UUID] = None
    status: StatusOS
    visualizacao_hash: UUID
    data_abertura: datetime
    data_notificacao_cliente: Optional[datetime] = None
    data_resposta_cliente: Optional[datetime] = None
    tempo_espera_aprovacao_minutos: Optional[int] = None
    observacoes_cliente: Optional[str] = None

    itens_servico: List[ItemServicoResponse]
    itens_peca: List[ItemPecaResponse]

    model_config = ConfigDict(from_attributes=True)
