from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    AliasPath,
)

from app.features.ordens_servico.models import StatusOS


class ItemServicoRequest(BaseModel):
    """Serviço solicitado na abertura da OS."""

    servico_id: UUID = Field(
        ...,
        description="ID do serviço do catálogo",
    )


class ItemPecaRequest(BaseModel):
    """Peça e quantidade solicitadas na abertura da OS."""

    peca_id: UUID = Field(
        ...,
        description="ID da peça do estoque",
    )

    quantidade: int = Field(
        ...,
        gt=0,
        description="Quantidade demandada",
    )


class CriarOrdemServicoRequest(BaseModel):
    """Dados necessários para realizar o Check-in."""

    cliente_id: UUID = Field(
        ...,
        description="ID do cliente",
    )

    veiculo_id: UUID = Field(
        ...,
        description="ID do veículo",
    )

    servicos_solicitados: List[ItemServicoRequest] = Field(
        default_factory=list,
        description="Serviços solicitados no check-in",
    )

    pecas_solicitadas: List[ItemPecaRequest] = Field(
        default_factory=list,
        description="Peças previamente solicitadas",
    )


class ItemServicoResponse(BaseModel):
    """
    Representação do serviço efetivamente anexado à OS.

    ORM:
        ItemServicoOS.servico_base_id
        ItemServicoOS.servico_base.nome

    API:
        servico_id
        nome
    """

    servico_id: UUID = Field(validation_alias=AliasPath("servico_base_id"))

    nome: str = Field(
        validation_alias=AliasPath(
            "servico_base",
            "nome",
        )
    )

    preco_aplicado: Decimal
    duracao_minutos: int

    model_config = ConfigDict(from_attributes=True)


class ItemPecaResponse(BaseModel):
    """
    Representação da peça efetivamente anexada à OS.

    ORM:
        ItemPecaOS.peca_id
        ItemPecaOS.peca.nome

    API:
        peca_id
        nome_peca
    """

    peca_id: UUID

    quantidade: int

    preco_unitario_aplicado: Decimal

    nome_peca: str = Field(
        validation_alias=AliasPath(
            "peca",
            "nome",
        )
    )

    model_config = ConfigDict(from_attributes=True)


class OrdemServicoResponse(BaseModel):
    """Resposta detalhada da OS."""

    id: UUID

    cliente_id: UUID

    veiculo_id: UUID

    mecanico_id: Optional[UUID] = None

    status: StatusOS

    visualizacao_hash: UUID

    data_abertura: datetime

    data_conclusao: Optional[datetime] = None

    itens_servico: List[ItemServicoResponse] = Field(default_factory=list)

    itens_peca: List[ItemPecaResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
