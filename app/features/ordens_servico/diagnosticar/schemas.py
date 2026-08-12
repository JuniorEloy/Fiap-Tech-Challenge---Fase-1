from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, AliasPath
from app.features.ordens_servico.models import StatusOS


class ItemServicoRequest(BaseModel):
    """Schema: Identificador do serviço adicionado no diagnóstico."""

    servico_id: UUID = Field(..., description="ID do serviço base no catálogo")


class ItemPecaRequest(BaseModel):
    """Schema: Peça e quantidade identificadas para reposição."""

    peca_id: UUID = Field(..., description="ID da peça no estoque")
    quantidade: int = Field(
        ..., gt=0, description="Quantidade física de peças demandada"
    )


class LancarDiagnosticoRequest(BaseModel):
    """Schema de Entrada: Lista de serviços e peças identificados na avaliação técnica do mecânico."""

    servicos: List[ItemServicoRequest] = Field(
        ...,
        min_length=1,
        description="Lista de serviços técnicos que devem ser realizados (mão de obra)",
    )
    pecas: List[ItemPecaRequest] = Field(
        default_factory=list,
        description="Lista opcional de peças de reposição que serão consumidas",
    )


class ItemServicoResponse(BaseModel):
    """Schema de Saída: Representação do serviço com congelamento de preço histórico."""

    servico_id: UUID = Field(validation_alias="servico_base_id")
    nome: str = Field(validation_alias=AliasPath("servico_base", "nome"))
    preco_aplicado: Decimal
    duracao_minutos: int

    model_config = ConfigDict(from_attributes=True)


class ItemPecaResponse(BaseModel):
    """Schema de Saída: Representação de peças com congelamento de preços de venda."""

    peca_id: UUID
    nome_peca: str = Field(validation_alias=AliasPath("peca", "nome"))
    quantidade: int
    preco_unitario_aplicado: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrdemServicoResponse(BaseModel):
    """Schema de Saída: Detalhamento completo da Ordem de Serviço atualizada pós-diagnóstico."""

    id: UUID
    cliente_id: UUID
    veiculo_id: UUID
    mecanico_id: Optional[UUID] = None
    status: StatusOS
    visualizacao_hash: UUID
    data_abertura: datetime
    data_conclusao: Optional[datetime] = None
    data_notificacao_cliente: Optional[datetime] = None
    data_resposta_cliente: Optional[datetime] = None

    itens_servico: List[ItemServicoResponse] = Field(default_factory=list)
    itens_peca: List[ItemPecaResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
