from collections import defaultdict
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.ordens_servico.models import OrdemServico, StatusOS
from app.features.relatorios.tempo_medio.schemas import (
    RelatorioTempoMedioResponse,
    TempoMedioPorEtapaResponse,
)


class RelatorioTempoMedioQueryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def obter_relatorio_tempos(self) -> RelatorioTempoMedioResponse:
        """
        Calcula de forma analítica os tempos médios operacionais e a eficiência do pátio:
        1. Executa uma agregação direta sobre os KPIs já gravados desnormalizados na OS.
        2. Carrega as OSs finalizadas e seus logs de transição (FSM) para calcular
           a permanência média exata em cada etapa.
        """
        # 1. Totalizadores e médias agregadas a partir dos carimbos desnormalizados
        query_agregada = select(
            func.count(OrdemServico.id).label("total"),
            func.avg(OrdemServico.leadtime_full_minutos).label("avg_full"),
            func.avg(OrdemServico.leadtime_ativo_minutos).label("avg_ativo"),
            func.avg(OrdemServico.tempo_espera_aprovacao_minutos).label("avg_espera"),
        ).where(OrdemServico.leadtime_full_minutos.isnot(None))
        res_agregada = await self.db.execute(query_agregada)
        row = res_agregada.one()

        total = row.total or 0
        avg_full = int(row.avg_full) if row.avg_full is not None else 0
        avg_ativo = int(row.avg_ativo) if row.avg_ativo is not None else 0
        avg_espera = int(row.avg_espera) if row.avg_espera is not None else 0

        # 2. Carrega todas as OSs finalizadas com seus logs de status (selectinload)
        query_os = (
            select(OrdemServico)
            .options(selectinload(OrdemServico.logs_status))
            .where(OrdemServico.leadtime_full_minutos.isnot(None))
        )
        res_os = await self.db.execute(query_os)
        ordens = res_os.scalars().all()

        # 3. Mapeamento analítico de permanência por etapa
        tempos_por_etapa = defaultdict(list)

        for os in ordens:
            # Ponto de partida: O carro entra em RECEBIDA na data de abertura
            ultimo_status = "RECEBIDA"
            ultimo_timestamp = os.data_abertura

            # Ordena os logs cronologicamente para remontar a jornada
            logs_ordenados = sorted(os.logs_status, key=lambda l: l.data_transicao)

            for log in logs_ordenados:
                # O tempo gasto na etapa anterior é o tempo decorrido até a transição
                duracao_minutos = (
                    log.data_transicao - ultimo_timestamp
                ).total_seconds() / 60

                # Validação para prevenir ruídos ou flutuações de segundos negativos
                if duracao_minutos > 0:
                    tempos_por_etapa[ultimo_status].append(duracao_minutos)

                ultimo_status = getattr(log.status_novo, "value", log.status_novo)
                ultimo_timestamp = log.data_transicao

        # 4. Consolida as médias aritméticas por etapa operacional
        def calcular_media(status_key: str) -> int:
            lista_tempos = tempos_por_etapa.get(status_key, [])
            if not lista_tempos:
                return 0
            return int(sum(lista_tempos) / len(lista_tempos))

        por_etapa_dto = TempoMedioPorEtapaResponse(
            RECEBIDA=calcular_media("RECEBIDA"),
            EM_DIAGNOSTICO=calcular_media("EM_DIAGNOSTICO"),
            AGUARDANDO_APROVACAO=calcular_media("AGUARDANDO_APROVACAO"),
            EM_EXECUCAO=calcular_media("EM_EXECUCAO"),
        )

        return RelatorioTempoMedioResponse(
            total_ordens_avaliadas=total,
            tempo_medio_geral_minutos=avg_full,
            tempo_medio_trabalho_ativo_minutos=avg_ativo,
            tempo_medio_espera_aprovacao_minutos=avg_espera,
            tempo_medio_por_etapa_minutos=por_etapa_dto,
        )
