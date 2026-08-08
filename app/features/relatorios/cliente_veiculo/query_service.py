from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.clientes.models import Cliente
from app.features.veiculos.models import Veiculo
from app.features.relatorios.cliente_veiculo.schemas import (
    DashboardGeralResponse,
    ClienteResumoDTO,
    VeiculoResumoDTO,
)
from app.shared.domain.value_objects.cpf_cnpj import CpfCnpj
from app.shared.domain.value_objects.placa import Placa


class DashboardQueryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def obter_dados_gerais(self) -> DashboardGeralResponse:
        """
        Recupera dados analíticos cruzando informações de faturamento e operações.
        Retorna projeções otimizadas para leitura.
        """
        # 1. Totalizadores rápidos de auditoria
        total_cli_res = await self.db.execute(select(func.count(Cliente.id)))
        total_clientes = total_cli_res.scalar_one()

        total_vei_res = await self.db.execute(select(func.count(Veiculo.id)))
        total_veiculos = total_vei_res.scalar_one()

        # 2. Clientes cadastrados com a contagem agregada de veículos (Left Outer Join)
        query_clientes = (
            select(
                Cliente.id,
                Cliente.nome,
                Cliente.email,
                Cliente.cpf_cnpj,
                func.count(Veiculo.id).label("total_veiculos"),
            )
            .outerjoin(Veiculo, Veiculo.cliente_id == Cliente.id)
            .group_by(Cliente.id, Cliente.nome, Cliente.email, Cliente.cpf_cnpj)
        )
        res_clientes = await self.db.execute(query_clientes)
        clientes_list = []
        for row in res_clientes:
            clientes_list.append(
                ClienteResumoDTO(
                    id=row.id,
                    nome=row.nome,
                    email=row.email,
                    cpf_cnpj=CpfCnpj(
                        row.cpf_cnpj
                    ).formatado,  # Formatação rica na camada DTO
                    total_veiculos=row.total_veiculos,
                )
            )

        # 3. Veículos da oficina com o nome correspondente do seu Proprietário (Inner Join)
        query_veiculos = select(
            Veiculo.id,
            Veiculo.placa,
            Veiculo.marca,
            Veiculo.modelo,
            Cliente.nome.label("nome_proprietario"),
        ).join(Cliente, Veiculo.cliente_id == Cliente.id)
        res_veiculos = await self.db.execute(query_veiculos)
        veiculos_list = []
        for row in res_veiculos:
            veiculos_list.append(
                VeiculoResumoDTO(
                    id=row.id,
                    placa=Placa(row.placa).formatada,
                    marca=row.marca,
                    modelo=row.modelo,
                    nome_proprietario=row.nome_proprietario,
                )
            )

        return DashboardGeralResponse(
            total_clientes=total_clientes,
            total_veiculos=total_veiculos,
            clientes=clientes_list,
            veiculos=veiculos_list,
        )
