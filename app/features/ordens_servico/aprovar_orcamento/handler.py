from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.features.ordens_servico.models import OrdemServico, StatusOS
from app.features.ordens_servico.repository import OrdemServicoRepository
from app.features.ordens_servico.aprovar_orcamento.schemas import (
    ResponderOrcamentoRequest,
    RespostaOrcamentoResponse,
)
from app.features.estoque.models import PecaInsumo
from typing import Optional


class ResponderOrcamentoHandler:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = OrdemServicoRepository(db)

    async def executar(
        self,
        os_id: UUID,
        command: ResponderOrcamentoRequest,
        operador_id: Optional[UUID] = None,
    ) -> RespostaOrcamentoResponse:
        """
        Orquestra a aprovação ou rejeição da Ordem de Serviço pelo cliente:
        1. Localiza a OS ativa no pátio e valida o status atual (precisa estar em AGUARDANDO_APROVACAO).
        2. Se aprovado:
           a. Adquire bloqueio pessimista (SELECT FOR UPDATE) sobre os insumos de estoque listados na OS.
           b. Valida se há saldo em estoque suficiente para todos os itens requeridos.
           c. Decrementa o saldo físico no estoque (quantidade_em_estoque).
           d. Transiciona o status da OS para EM_EXECUCAO via FSM.
        3. Se rejeitado:
           a. Transiciona o status da OS para CANCELADA.
        4. Registra observações, calcula tempos de espera (KPI).
        5. Persiste o log de auditoria de status e executa o commit completo.
        """
        # 1. Carrega a OS com seus itens (eager loading habilitado pelo repositório)
        os = await self.repository.buscar_por_id(os_id)
        if not os:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ordem de Serviço não encontrada no sistema.",
            )

        # 2. Garante que a OS está aguardando decisão do cliente
        if os.status != StatusOS.AGUARDANDO_APROVACAO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Não é possível responder a um orçamento de uma OS no status atual: {getattr(os.status, 'value', os.status)}.",
            )

        # Armazena observações, se fornecidas
        if command.observacoes_cliente:
            os.observacoes_cliente = command.observacoes_cliente

        # 3. Lógica baseada na decisão (Aprovação ou Rejeição)
        if command.aprovado:
            # --- BAIXA DE ESTOQUE COM LOCK PESSIMISTA ---
            if os.itens_peca:
                peca_ids = [item.peca_id for item in os.itens_peca]

                # Executa select com FOR UPDATE para evitar Race Conditions
                query_estoque = (
                    select(PecaInsumo)
                    .where(PecaInsumo.id.in_(peca_ids))
                    .with_for_update()  # 🌟 LOCK PESSIMISTA ATIVO!
                )
                res_estoque = await self.db.execute(query_estoque)
                pecas_db = {p.id: p for p in res_estoque.scalars().all()}

                # Valida se as peças existem e se há estoque suficiente
                for item in os.itens_peca:
                    peca_estoque = pecas_db.get(item.peca_id)
                    if not peca_estoque:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Peça ou insumo com ID {item.peca_id} não encontrado no catálogo.",
                        )

                    if peca_estoque.quantidade_em_estoque < item.quantidade:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=(
                                f"Saldo insuficiente no estoque para a peça '{peca_estoque.nome}'. "
                                f"Necessário: {item.quantidade}, Disponível: {peca_estoque.quantidade_em_estoque}."
                            ),
                        )

                    # Decrementa o saldo físico no estoque (baixa efetiva)
                    peca_estoque.quantidade_em_estoque -= item.quantidade

            # Transiciona status: AGUARDANDO_APROVACAO -> EM_EXECUCAO
            log_status = os.alterar_status(
                StatusOS.EM_EXECUCAO, operador_id=operador_id
            )

        else:
            # Transiciona status: AGUARDANDO_APROVACAO -> CANCELADA
            log_status = os.alterar_status(StatusOS.CANCELADA, operador_id=operador_id)

        # 4. Salva o log de auditoria de status
        await self.repository.salvar_status_log(log_status)

        # 5. Commita a transação completa de forma atômica
        await self.db.commit()

        # Retorna o DTO estruturado via model_validate
        return RespostaOrcamentoResponse.model_validate(os)

    async def executar_via_hash(
        self, hash_visualizacao: UUID, command: ResponderOrcamentoRequest
    ) -> RespostaOrcamentoResponse:
        """
        Permite que o cliente responda ao orçamento através de um link público e seguro (via hash),
        sem exigir autenticação JWT de operador interno.
        """
        # Busca a OS no banco usando o hash de visualização único
        query_os = select(OrdemServico).where(
            OrdemServico.visualizacao_hash == hash_visualizacao
        )
        result = await self.db.execute(query_os)
        os = result.scalar_one_or_none()

        if not os:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ordem de Serviço não encontrada com o hash de visualização fornecido.",
            )

        # Executa o fluxo padrão usando o ID do próprio cliente como o operador que assinou
        return await self.executar(os_id=os.id, command=command, operador_id=None)
