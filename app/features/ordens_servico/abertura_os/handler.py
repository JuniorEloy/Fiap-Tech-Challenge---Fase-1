from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from uuid import uuid7

from app.features.ordens_servico.models import (
    OrdemServico,
    StatusOS,
    ItemServicoOS,
    ItemPecaOS,
)
from app.features.ordens_servico.repository import OrdemServicoRepository
from app.features.ordens_servico.abertura_os.schemas import (
    CriarOrdemServicoRequest,
    OrdemServicoResponse,
)

# Importação dos modelos externos para validação física
from app.features.usuarios.models import Usuario
from app.features.veiculos.models import Veiculo
from app.features.servicos.models import ServicoBase
from app.features.estoque.models import PecaInsumo
from app.features.clientes.models import Cliente

class CriarOrdemServicoHandler:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = OrdemServicoRepository(db)

    async def executar(
        self, command: CriarOrdemServicoRequest, operador_id: UUID
    ) -> OrdemServicoResponse:
        """
        Orquestra a criação de uma nova Ordem de Serviço (Check-in) e valida o fluxo expresso.
        """
        # 1. Valida se o Cliente existe e está ativo
        res_cli = await self.db.execute(select(Cliente).where(Cliente.id == command.cliente_id))
        cliente = res_cli.scalar_one_or_none()
        
        # Checa de forma resiliente o campo 'ativo' (caso exista ou não no modelo Cliente)
        cliente_ativo = getattr(cliente, "ativo", True)
        if not cliente or not cliente_ativo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente associado não encontrado ou inativo no sistema."
            )

        # 2. Valida se o Veículo existe
        res_vei = await self.db.execute(
            select(Veiculo).where(Veiculo.id == command.veiculo_id)
        )
        veiculo = res_vei.scalar_one_or_none()
        if not veiculo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Veículo associado não cadastrado.",
            )

        # 3. Instancia a OS no status inicial RECEBIDA
        os_id_gerado = uuid7()
        os = OrdemServico(
            id=os_id_gerado,
            cliente_id=command.cliente_id,
            veiculo_id=command.veiculo_id,
            status=StatusOS.RECEBIDA,
        )
        await self.repository.salvar(os)

        # 4. Processa os itens se existirem e decide se é um Orçamento Expresso
        is_expresso = False
        servicos_entidades = []
        pecas_entidades_map = {}

        if command.servicos_solicitados:
            # Busca todos os serviços informados
            servico_ids = [item.servico_id for item in command.servicos_solicitados]
            res_serv = await self.db.execute(
                select(ServicoBase).where(ServicoBase.id.in_(servico_ids))
            )
            servicos_entidades = res_serv.scalars().all()

            if len(servicos_entidades) != len(command.servicos_solicitados):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Um ou mais serviços informados não constam no catálogo.",
                )

            # Regra de Negócio: Todos os serviços informados precisam aceitar o fluxo expresso!
            is_expresso = all(s.permite_servico_expresso for s in servicos_entidades)

            # Se houver peças solicitadas no check-in, busca-as para validação e preço
            if command.pecas_solicitadas:
                peca_ids = [item.peca_id for item in command.pecas_solicitadas]
                res_pecas = await self.db.execute(
                    select(PecaInsumo).where(PecaInsumo.id.in_(peca_ids))
                )
                pecas_list = res_pecas.scalars().all()

                if len(pecas_list) != len(command.pecas_solicitadas):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Uma ou mais peças informadas não existem no estoque.",
                    )
                pecas_entidades_map = {p.id: p for p in pecas_list}

        # 5. Adiciona os itens se for elegível ao fluxo Expresso
        if is_expresso:
            # Adiciona serviços congelando preços históricos
            for s in servicos_entidades:
                item_serv = ItemServicoOS(
                    ordem_servico_id=os.id,
                    servico_base_id=s.id,
                    preco_aplicado=s.preco_mao_de_obra,
                    duracao_minutos=s.duracao_estimada_minutos,
                )
                os.itens_servico.append(item_serv)

            # Adiciona peças congelando preço unitário histórico
            for p_req in command.pecas_solicitadas:
                p_db = pecas_entidades_map[p_req.peca_id]
                item_peca = ItemPecaOS(
                    ordem_servico_id=os.id,
                    peca_id=p_req.peca_id,
                    quantidade=p_req.quantidade,
                    preco_unitario_aplicado=p_db.preco_venda,
                )
                os.itens_peca.append(item_peca)

            # Transiciona automaticamente de RECEBIDA para AGUARDANDO_APROVACAO
            log_status = os.alterar_status(
                StatusOS.AGUARDANDO_APROVACAO, operador_id=operador_id
            )
            await self.repository.salvar_status_log(log_status)

        else:
            # Caso contrário, força o carro para o fluxo de diagnóstico técnico padrão
            log_status = os.alterar_status(
                StatusOS.EM_DIAGNOSTICO, operador_id=operador_id
            )
            await self.repository.salvar_status_log(log_status)

        # 6. Salva as alterações na transação do banco
        await self.db.commit()

        await self.db.refresh(os, attribute_names=["itens_servico", "itens_peca", "logs_status"])

        return OrdemServicoResponse.model_validate(os)
