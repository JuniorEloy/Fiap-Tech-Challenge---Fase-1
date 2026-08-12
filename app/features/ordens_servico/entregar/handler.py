from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from decimal import Decimal

from app.features.ordens_servico.models import OrdemServico, StatusOS
from app.features.ordens_servico.repository import OrdemServicoRepository
from app.features.ordens_servico.entregar.schemas import (
    RegistrarEntregaRequest,
    EntregaOSResponse,
)


class RegistrarEntregaHandler:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = OrdemServicoRepository(db)

    async def executar(
        self, os_id: UUID, command: RegistrarEntregaRequest, operador_id: UUID
    ) -> EntregaOSResponse:
        """
        Orquestra a entrega do veículo e encerramento financeiro no caixa:
        1. Localiza a OS ativa e garante que ela está no status FINALIZADA.
        2. Registra os metadados de pagamento (forma de pagamento, comprovante).
        3. Realiza a transição física da OS para ENTREGUE via FSM.
        4. Calcula e consolida os valores financeiros de faturamento final.
        5. Grava transacionalmente no banco, insere o log de status e commita.
        """
        # 1. Busca a OS com os relacionamentos carregados (eager load)
        os = await self.repository.buscar_por_id(os_id)
        if not os:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ordem de Serviço não encontrada no sistema.",
            )

        # 2. Valida se a manutenção física foi concluída (estágio FINALIZADA)
        if os.status != StatusOS.FINALIZADA:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Não é possível entregar veículo de uma OS que não está finalizada. "
                    f"Status atual: {getattr(os.status, 'value', os.status)}."
                ),
            )

        # 3. Registra dados do Caixa (Faturamento)
        os.forma_pagamento = command.forma_pagamento.value
        os.comprovante_transacao = command.comprovante_transacao

        # 4. Consolida valores financeiros de fechamento de caixa
        valor_servicos = sum(
            Decimal(str(item.preco_aplicado)) for item in os.itens_servico
        )
        valor_pecas = sum(
            Decimal(str(item.preco_unitario_aplicado)) * item.quantidade
            for item in os.itens_peca
        )

        os.valor_total_servicos = valor_servicos
        os.valor_total_pecas = valor_pecas
        os.valor_total_os = valor_servicos + valor_pecas

        # 5. Transiciona status de FSM: FINALIZADA -> ENTREGUE
        log_status = os.alterar_status(StatusOS.ENTREGUE, operador_id=operador_id)
        await self.repository.salvar_status_log(log_status)

        # 6. Commita de forma transacional e atômica no PostgreSQL
        await self.db.commit()
        await self.db.refresh(os)

        return EntregaOSResponse.model_validate(os)
