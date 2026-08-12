from uuid import UUID, uuid7

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.ordens_servico.models import (
    OrdemServico,
    StatusOS,
    ItemServicoOS,
    ItemPecaOS,
)

from app.features.ordens_servico.repository import (
    OrdemServicoRepository,
)

from app.features.ordens_servico.abrir.schemas import (
    CriarOrdemServicoRequest,
    OrdemServicoResponse,
)

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
        self,
        command: CriarOrdemServicoRequest,
        operador_id: UUID,
    ) -> OrdemServicoResponse:

        # ============================================================
        # 1. VALIDA CLIENTE
        # ============================================================

        result = await self.db.execute(
            select(Cliente).where(Cliente.id == command.cliente_id)
        )

        cliente = result.scalar_one_or_none()

        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente associado não encontrado.",
            )

        cliente_ativo = getattr(
            cliente,
            "ativo",
            True,
        )

        if not cliente_ativo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente associado está inativo.",
            )

        # ============================================================
        # 2. VALIDA VEÍCULO
        # ============================================================

        result = await self.db.execute(
            select(Veiculo).where(Veiculo.id == command.veiculo_id)
        )

        veiculo = result.scalar_one_or_none()

        if not veiculo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Veículo associado não cadastrado.",
            )

        # ============================================================
        # 3. BUSCA SERVIÇOS
        # ============================================================

        servicos_entidades: list[ServicoBase] = []

        if command.servicos_solicitados:
            servico_ids = [item.servico_id for item in command.servicos_solicitados]

            result = await self.db.execute(
                select(ServicoBase).where(ServicoBase.id.in_(servico_ids))
            )

            servicos_entidades = list(result.scalars().all())

            encontrados = {servico.id for servico in servicos_entidades}

            faltantes = [
                servico_id
                for servico_id in servico_ids
                if servico_id not in encontrados
            ]

            if faltantes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=("Um ou mais serviços informados não constam no catálogo."),
                )

        # ============================================================
        # 4. BUSCA PEÇAS
        # ============================================================

        pecas_entidades_map: dict[UUID, PecaInsumo] = {}

        if command.pecas_solicitadas:
            peca_ids = [item.peca_id for item in command.pecas_solicitadas]

            result = await self.db.execute(
                select(PecaInsumo).where(PecaInsumo.id.in_(peca_ids))
            )

            pecas_entidades = list(result.scalars().all())

            pecas_entidades_map = {peca.id: peca for peca in pecas_entidades}

            faltantes = [
                peca_id for peca_id in peca_ids if peca_id not in pecas_entidades_map
            ]

            if faltantes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=("Uma ou mais peças informadas não existem no estoque."),
                )

        # ============================================================
        # 5. DEFINE FLUXO
        # ============================================================

        is_expresso = bool(servicos_entidades) and all(
            servico.permite_servico_expresso for servico in servicos_entidades
        )

        # ============================================================
        # 6. CRIA OS
        # ============================================================

        os = OrdemServico(
            id=uuid7(),
            cliente_id=command.cliente_id,
            veiculo_id=command.veiculo_id,
            status=StatusOS.RECEBIDA,
        )

        self.db.add(os)

        # ============================================================
        # 7. FLUXO EXPRESSO
        # ============================================================

        if is_expresso:
            itens_servico = [
                ItemServicoOS(
                    ordem_servico_id=os.id,
                    servico_base_id=servico.id,
                    preco_aplicado=servico.preco_mao_de_obra,
                    duracao_minutos=(servico.duracao_estimada_minutos),
                )
                for servico in servicos_entidades
            ]

            itens_peca = [
                ItemPecaOS(
                    ordem_servico_id=os.id,
                    peca_id=item.peca_id,
                    quantidade=item.quantidade,
                    preco_unitario_aplicado=(
                        pecas_entidades_map[item.peca_id].preco_venda
                    ),
                )
                for item in command.pecas_solicitadas
            ]

            self.db.add_all(itens_servico)
            self.db.add_all(itens_peca)

            log_status = os.alterar_status(
                StatusOS.AGUARDANDO_APROVACAO,
                operador_id=operador_id,
            )

            self.db.add(log_status)

        # ============================================================
        # 8. FLUXO NORMAL
        # ============================================================

        else:
            log_status = os.alterar_status(
                StatusOS.EM_DIAGNOSTICO,
                operador_id=operador_id,
            )

            self.db.add(log_status)

        # ============================================================
        # 9. COMMIT
        # ============================================================

        await self.db.commit()

        # ============================================================
        # 10. RECARREGA TUDO NECESSÁRIO PARA O RESPONSE
        # ============================================================

        result = await self.db.execute(
            select(OrdemServico)
            .where(OrdemServico.id == os.id)
            .options(
                # ItemServicoOS
                selectinload(OrdemServico.itens_servico).selectinload(
                    ItemServicoOS.servico_base
                ),
                # ItemPecaOS
                selectinload(OrdemServico.itens_peca).selectinload(ItemPecaOS.peca),
                # Logs
                selectinload(OrdemServico.logs_status),
            )
        )

        os = result.scalar_one()

        # ============================================================
        # 11. RESPONSE
        # ============================================================

        return OrdemServicoResponse.model_validate(
            os,
            from_attributes=True,
        )
