from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.features.ordens_servico.models import StatusOS


class ItemServicoRequest(BaseModel):
    """Schema: Identificador do serviço solicitado na abertura (Check-in)."""

    servico_id: UUID = Field(
        ..., description="ID do serviço do catálogo (ex: Troca de Óleo)"
    )


class ItemPecaRequest(BaseModel):
    """Schema: Peça e quantidade solicitadas previamente (ex: Filtro de óleo)."""

    peca_id: UUID = Field(..., description="ID da peça do estoque")
    quantidade: int = Field(..., gt=0, description="Quantidade demandada")


class CriarOrdemServicoRequest(BaseModel):
    """Schema de Entrada: Dados necessários para realizar o Check-in do veículo."""

    cliente_id: UUID = Field(..., description="ID do cliente (usuário cadastrado)")
    veiculo_id: UUID = Field(..., description="ID do veículo associado")

    # Listas opcionais para o caso de Serviço Expresso
    servicos_solicitados: List[ItemServicoRequest] = Field(
        default_factory=list,
        description="Lista de serviços conhecidos solicitados no check-in (ex: revisão simples)",
    )
    pecas_solicitadas: List[ItemPecaRequest] = Field(
        default_factory=list,
        description="Lista de peças que se sabe previamente que serão consumidas",
    )


class ItemServicoResponse(BaseModel):
    """Schema de Saída: Confirmação do serviço atrelado."""

    servico_id: UUID
    nome: str
    preco_aplicado: Decimal
    duracao_minutos: int

    model_config = ConfigDict(from_attributes=True)


class ItemPecaResponse(BaseModel):
    peca_id: UUID
    quantidade: int
    preco_unitario_aplicado: Decimal

    nome_peca: str

    @classmethod
    def model_validate(cls, obj):
        return cls(
            peca_id=obj.peca_id,
            quantidade=obj.quantidade,
            preco_unitario_aplicado=obj.preco_unitario_aplicado,
            nome_peca=obj.peca.nome,
        )


class OrdemServicoResponse(BaseModel):
    """Schema de Saída: Resposta detalhada da OS recém-criada (ou atualizada)."""

    id: UUID
    cliente_id: UUID
    veiculo_id: UUID
    mecanico_id: Optional[UUID] = None
    status: StatusOS
    visualizacao_hash: UUID
    data_abertura: datetime
    data_conclusao: Optional[datetime] = None

    # Itens anexados
    itens_servico: List[ItemServicoResponse]
    itens_peca: List[ItemPecaResponse]

    model_config = ConfigDict(from_attributes=True)
