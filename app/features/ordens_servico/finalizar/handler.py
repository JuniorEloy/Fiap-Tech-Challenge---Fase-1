from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from decimal import Decimal

from app.features.ordens_servico.models import StatusOS
from app.features.ordens_servico.repository import OrdemServicoRepository
from app.features.ordens_servico.finalizar.schemas import (
    FinalizarOrdemServicoRequest,
    FinalizacaoOSResponse,
)


class FinalizarOrdemServicoHandler:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = OrdemServicoRepository(db)

    async def executar(
        self, os_id: UUID, command: FinalizarOrdemServicoRequest, mecanico_id: UUID
    ) -> FinalizacaoOSResponse:
        """
        Orquestra a finalização e conclusão de serviços de uma Ordem de Serviço:
        1. Localiza a OS ativa no pátio com carregamento prévio das coleções de itens.
        2. Garante que a OS está no status correto (EM_EXECUCAO).
        3. Realiza a transição física do status da FSM para 'FINALIZADA'.
           a. A FSM calcula a data de conclusão automática.
           b. A FSM calcula os KPIs analíticos (leadtime_full_minutos e leadtime_ativo_minutos).
        4. Calcula os valores totais consolidados históricos para o faturamento (Serviços, Peças e Total).
        5. Persiste o log de auditoria e executa o commit da transação de forma segura.
        """
        # 1. Busca a OS com eager-loading habilitado pelo repositório (selectinload)
        os = await self.repository.buscar_por_id(os_id)
        if not os:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ordem de Serviço não encontrada no sistema.",
            )

        # 2. Valida se a OS está em andamento (manutenção ativa)
        if os.status != StatusOS.EM_EXECUCAO:
            status_atual = getattr(os.status, "value", os.status)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Não é possível concluir uma OS que não está em execução. Status atual: {status_atual}.",
            )

        # 3. Adiciona observações finais se fornecidas
        if command.observacoes_finais:
            os.observacoes_cliente = f"[Mecânico]: {command.observacoes_finais}"

        # 4. Transiciona status: EM_EXECUCAO -> FINALIZADA
        log_status = os.alterar_status(StatusOS.FINALIZADA, operador_id=mecanico_id)
        await self.repository.salvar_status_log(log_status)

        # 5. Calcula dinamicamente os valores de faturamento com base nos preços congelados
        valor_servicos = sum(item.preco_aplicado for item in os.itens_servico)
        valor_pecas = sum(
            item.preco_unitario_aplicado * item.quantidade for item in os.itens_peca
        )
        valor_total = valor_servicos + valor_pecas

        # 6. Grava tudo de forma transacional no banco
        await self.db.commit()

        # 7. Refresh para reidratar os relacionamentos de forma segura e limpa
        await self.db.refresh(os)

        # 8. Injeta os campos financeiros calculados dinamicamente de forma transiente na entidade
        # para que o model_validate do Pydantic consiga extraí-los automaticamente do objeto
        os.valor_servicos = Decimal(valor_servicos)
        os.valor_pecas = Decimal(valor_pecas)
        os.valor_total = Decimal(valor_total)

        return FinalizacaoOSResponse.model_validate(os)
