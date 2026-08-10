from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.estoque.models import PecaInsumo
from app.features.estoque.relatorio_estoque_baixo.schemas import (
    RelatorioEstoqueBaixoResponse,
    PecaEstoqueBaixoDTO,
)


class RelatorioEstoqueBaixoQueryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def obter_relatorio_critico(self) -> RelatorioEstoqueBaixoResponse:
        """
        Executa a projeção analítica para listar itens que violaram o limite de segurança.
        Ordena os itens de forma que os que possuem maior déficit de estoque apareçam primeiro.
        """
        # Busca todas as peças cujo estoque atual seja estritamente menor que o limite mínimo
        stmt = (
            select(PecaInsumo)
            .where(PecaInsumo.quantidade_em_estoque < PecaInsumo.limite_minimo)
            .order_by(
                (PecaInsumo.limite_minimo - PecaInsumo.quantidade_em_estoque).desc()
            )
        )

        result = await self.db.execute(stmt)
        pecas_criticas = result.scalars().all()

        itens_dto = []
        custo_total_reposicao = Decimal("0.00")

        for peca in pecas_criticas:
            unidades_em_falta = peca.limite_minimo - peca.quantidade_em_estoque
            # Se por algum motivo as unidades forem negativas, consideramos zero
            unidades_em_falta = max(0, unidades_em_falta)

            capital_necessario = Decimal(str(unidades_em_falta)) * peca.preco_custo

            itens_dto.append(
                PecaEstoqueBaixoDTO(
                    id=peca.id,
                    nome=peca.nome,
                    quantidade_em_estoque=peca.quantidade_em_estoque,
                    limite_minimo=peca.limite_minimo,
                    unidades_em_falta=unidades_em_falta,
                    preco_custo_referencia=peca.preco_custo,
                    capital_necessario_reposicao=capital_necessario,
                )
            )
            custo_total_reposicao += capital_necessario

        return RelatorioEstoqueBaixoResponse(
            total_itens_criticos=len(itens_dto),
            custo_total_estimado_reposicao=custo_total_reposicao,
            itens=itens_dto,
        )
