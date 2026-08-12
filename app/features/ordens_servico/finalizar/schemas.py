from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, AliasPath
from app.features.ordens_servico.models import StatusOS


class FinalizarOrdemServicoRequest(BaseModel):
    """Schema de Entrada: Registro de conclusão dos serviços técnicos."""
    observacoes_finais: Optional[str] = Field(
        None,
        max_length=255,
        description="Relato final do mecânico sobre o serviço executado (diagnóstico concluído, peças trocadas)"
    )


class ItemServicoResponse(BaseModel):
    """Schema de Saída: Confirmação de serviço executado."""
    servico_id: UUID = Field(validation_alias="servico_base_id")
    nome: str = Field(validation_alias=AliasPath("servico_base", "nome"))
    preco_aplicado: Decimal
    duracao_minutos: int

    model_config = ConfigDict(from_attributes=True)


class ItemPecaResponse(BaseModel):
    """Schema de Saída: Confirmação de peça de reposição consumida."""
    peca_id: UUID
    nome_peca: str = Field(validation_alias=AliasPath("peca", "nome"))
    quantidade: int
    preco_unitario_aplicado: Decimal

    model_config = ConfigDict(from_attributes=True)


class FinalizacaoOSResponse(BaseModel):
    """Schema de Saída: Detalhamento de KPIs operacionais e faturamento final."""
    id: UUID
    cliente_id: UUID
    veiculo_id: UUID
    mecanico_id: Optional[UUID] = None
    status: StatusOS
    data_abertura: datetime
    data_conclusao: datetime

    # KPIs desnormalizados gerados pela FSM
    leadtime_full_minutos: int = Field(..., description="Tempo total decorrido do veículo na oficina (abertura até conclusão)")
    leadtime_ativo_minutos: int = Field(..., description="Tempo líquido de manutenção física (excluindo tempo de espera de aprovação)")

    # Campos Financeiros Calculados Dinamicamente
    valor_servicos: Decimal = Field(..., description="Soma dos serviços prestados (mão de obra)")
    valor_pecas: Decimal = Field(..., description="Soma das peças e insumos de estoque aplicados")
    valor_total: Decimal = Field(..., description="Valor final faturado e consolidado para cobrança")

    itens_servico: List[ItemServicoResponse] = Field(default_factory=list)
    itens_peca: List[ItemPecaResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)