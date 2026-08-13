from typing import Dict
from pydantic import BaseModel, Field, ConfigDict


class TempoMedioPorEtapaResponse(BaseModel):
    """Schema: Tempo médio de permanência do veículo em cada status operacional."""

    RECEBIDA: int = Field(0, description="Tempo médio no status RECEBIDA em minutos")
    EM_DIAGNOSTICO: int = Field(
        0, description="Tempo médio no status EM_DIAGNOSTICO em minutos"
    )
    AGUARDANDO_APROVACAO: int = Field(
        0, description="Tempo médio no status AGUARDANDO_APROVACAO em minutos"
    )
    EM_EXECUCAO: int = Field(
        0, description="Tempo médio no status EM_EXECUCAO em minutos"
    )


class RelatorioTempoMedioResponse(BaseModel):
    """Schema de Saída: Resumo de tempos operacionais e eficiência de pátio."""

    total_ordens_avaliadas: int = Field(
        ..., description="Quantidade total de ordens de serviço concluídas no relatório"
    )
    tempo_medio_geral_minutos: int = Field(
        ...,
        description="Leadtime bruto médio (permanência física na oficina de ponta a ponta)",
    )
    tempo_medio_trabalho_ativo_minutos: int = Field(
        ...,
        description="Leadtime ativo médio (tempo em que a oficina esteve de fato trabalhando)",
    )
    tempo_medio_espera_aprovacao_minutos: int = Field(
        ...,
        description="Tempo de espera de aprovação médio (tempo de resposta do cliente)",
    )

    # KPIs específicos por etapa
    tempo_medio_por_etapa_minutos: TempoMedioPorEtapaResponse = Field(
        ..., description="Tempo médio detalhado gasto por status operacional"
    )

    model_config = ConfigDict(from_attributes=True)
