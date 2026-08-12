from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.features.ordens_servico.models import (
    OrdemServico,
    StatusOS,
    ItemServicoOS,
    ItemPecaOS,
)
from app.features.ordens_servico.repository import OrdemServicoRepository
from app.features.ordens_servico.diagnosticar.schemas import (
    LancarDiagnosticoRequest,
    OrdemServicoResponse,
)

from app.features.servicos.models import ServicoBase
from app.features.estoque.models import PecaInsumo


class LancarDiagnosticoHandler:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = OrdemServicoRepository(db)

    async def executar(
        self, os_id: UUID, command: LancarDiagnosticoRequest, mecanico_id: UUID
    ) -> OrdemServicoResponse:
        """
        Orquestra a finalização do diagnóstico técnico pelo mecânico:
        1. Localiza a OS ativa no pátio e valida se o status atual é EM_DIAGNOSTICO.
        2. Associa o mecânico autenticado ao veículo (responsabilidade técnica).
        3. Carrega os preços e tempos vigentes no catálogo de serviços e peças.
        4. Transiciona a OS para AGUARDANDO_APROVACAO e gera o log correspondente.
        5. Persiste as alterações e retorna o DTO estruturado.
        """
        # 1. Busca a OS no banco carregando as relações eager-loaded (selectinload) no repositório
        os = await self.repository.buscar_por_id(os_id)
        if not os:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ordem de Serviço não encontrada no sistema.",
            )

        # 2. Garante que a OS está no pátio aguardando diagnóstico técnico
        if os.status != StatusOS.EM_DIAGNOSTICO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Não é possível lançar diagnóstico para uma OS com status atual: {os.status.value}.",
            )

        # 3. Assume a responsabilidade técnica do veículo
        os.mecanico_id = mecanico_id

        # Limpa rascunhos ou solicitações anteriores para evitar lixo cadastral no banco de dados
        os.itens_servico.clear()
        os.itens_peca.clear()

        # 4. Processa e congela os Serviços do Catálogo
        servico_ids = [item.servico_id for item in command.servicos]
        res_serv = await self.db.execute(
            select(ServicoBase).where(ServicoBase.id.in_(servico_ids))
        )
        servicos_db = res_serv.scalars().all()

        if len(servicos_db) != len(command.servicos):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Um ou mais serviços técnicos informados não constam no catálogo oficial.",
            )

        servicos_map = {s.id: s for s in servicos_db}
        for s_req in command.servicos:
            s = servicos_map[s_req.servico_id]
            item_serv = ItemServicoOS(
                ordem_servico_id=os.id,
                servico_base_id=s.id,
                preco_aplicado=s.preco_mao_de_obra,
                duracao_minutos=s.duracao_estimada_minutos,
            )
            os.itens_servico.append(item_serv)

        # 5. Processa e congela as Peças do Estoque (se houver)
        if command.pecas:
            peca_ids = [item.peca_id for item in command.pecas]
            res_pecas = await self.db.execute(
                select(PecaInsumo).where(PecaInsumo.id.in_(peca_ids))
            )
            pecas_db = res_pecas.scalars().all()

            if len(pecas_db) != len(command.pecas):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uma ou mais peças de reposição solicitadas não existem em nosso estoque.",
                )

            pecas_map = {p.id: p for p in pecas_db}
            for p_req in command.pecas:
                p_db = pecas_map[p_req.peca_id]
                item_peca = ItemPecaOS(
                    ordem_servico_id=os.id,
                    peca_id=p_req.peca_id,
                    quantidade=p_req.quantidade,
                    preco_unitario_aplicado=p_db.preco_venda,
                )
                os.itens_peca.append(item_peca)

        # 6. Transiciona FSM de EM_DIAGNOSTICO -> AGUARDANDO_APROVACAO
        log_status = os.alterar_status(
            StatusOS.AGUARDANDO_APROVACAO, operador_id=mecanico_id
        )
        await self.repository.salvar_status_log(log_status)

        # 7. Persiste a transação de forma atômica no PostgreSQL
        await self.db.commit()

        # 8. Refresh para reidratar os relacionamentos com eager join (como item.peca para AliasPath)
        await self.db.refresh(os)

        return OrdemServicoResponse.model_validate(os)
