from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from decimal import Decimal

from app.features.ordens_servico.models import OrdemServico, StatusOS
from app.features.ordens_servico.repository import OrdemServicoRepository
from app.features.ordens_servico.entregar.schemas import (
    RegistrarEntregaRequest,
    EntregaOSResponse,
)

from app.shared.domain.ports.notificacao import EnviadorNotificacaoPort
from app.shared.domain.ports.pagamento import GatewayPagamentoPort


class RegistrarEntregaHandler:
    def __init__(
        self,
        db: AsyncSession,
        gateway_pagamento: GatewayPagamentoPort,
        notificador: EnviadorNotificacaoPort,
    ):
        self.db = db
        self.repository = OrdemServicoRepository(db)
        self.gateway = gateway_pagamento
        self.notificador = notificador

    async def executar(
        self, os_id: UUID, command: RegistrarEntregaRequest, operador_id: UUID
    ) -> EntregaOSResponse:
        """
        Orquestra a entrega do veículo e encerramento financeiro no caixa:
        1. Localiza a OS ativa e garante que ela está no status FINALIZADA.
        2. Registra os metadados de pagamento (forma de pagamento, comprovante).
        3. Valida transações de cartão de forma síncrona contra o Gateway de Pagamentos.
        4. Transiciona física da OS para ENTREGUE via FSM.
        5. Calcula e consolida os valores financeiros de faturamento final.
        6. Grava transacionalmente no banco, insere o log de status e commita.
        7. Envia notificação de conclusão para o WhatsApp do cliente.
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
        valor_total = valor_servicos + valor_pecas

        os.valor_total_servicos = valor_servicos
        os.valor_total_pecas = valor_pecas
        os.valor_total_os = valor_total

        # =========================================================================
        # INTEGRAÇÃO COM GATEWAY DE PAGAMENTO (PORTA EXTERNA)
        # =========================================================================
        # Se for pagamento eletrônico via cartão, bate no Gateway para processamento
        if command.forma_pagamento.value in ("CREDITO", "DEBITO"):
            token_cartao = command.comprovante_transacao or "token_padrao"
            resultado = await self.gateway.processar_pagamento(
                ordem_servico_id=os.id, valor=valor_total, token_cartao=token_cartao
            )
            # Se for recusado (ex: simulado com "9999" nos testes de recusa), cancela a entrega
            if not resultado.sucesso:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Não foi possível concluir a entrega. {resultado.mensagem}",
                )
            # Salva o ID autorizado pelo gateway como comprovante oficial da transação
            os.comprovante_transacao = resultado.transacao_id

        # 5. Transiciona status de FSM: FINALIZADA -> ENTREGUE
        log_status = os.alterar_status(StatusOS.ENTREGUE, operador_id=operador_id)
        await self.repository.salvar_status_log(log_status)

        # 6. Commita de forma transacional e atômica no PostgreSQL
        await self.db.commit()
        await self.db.refresh(os)

        # =========================================================================
        # INTEGRAÇÃO COM WHATSAPP (PORTA EXTERNA DE NOTIFICAÇÃO)
        # =========================================================================
        # Busca explicitamente o cliente e veículo de forma assíncrona para evitar erros de lazy loading
        from app.features.clientes.models import Cliente
        from app.features.veiculos.models import Veiculo

        query_cliente = select(Cliente).where(Cliente.id == os.cliente_id)
        res_cli = await self.db.execute(query_cliente)
        cliente = res_cli.scalar_one_or_none()

        query_veiculo = select(Veiculo).where(Veiculo.id == os.veiculo_id)
        res_vei = await self.db.execute(query_veiculo)
        veiculo = res_vei.scalar_one_or_none()

        if cliente and veiculo:
            await self.notificador.enviar_notificacao_conclusao(
                telefone=cliente.telefone,
                cliente_nome=cliente.nome,
                placa=veiculo.placa,
            )

        return EntregaOSResponse.model_validate(os)
