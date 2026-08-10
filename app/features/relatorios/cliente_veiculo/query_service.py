from collections import defaultdict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.clientes.models import Cliente
from app.features.veiculos.models import Veiculo
from app.features.relatorios.cliente_veiculo.schemas import (
    RelatorioClienteVeiculoResponse,
    ClienteRelatorioDTO,
    VeiculoRelatorioDTO,
)
from app.shared.domain.value_objects.cpf_cnpj import CpfCnpj
from app.shared.domain.value_objects.telefone import Telefone
from app.shared.domain.value_objects.placa import Placa


class RelatorioClienteVeiculoQueryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def obter_relatorio_geral(self) -> RelatorioClienteVeiculoResponse:
        """
        Executa uma projeção otimizada de leitura direta (CQRS).
        Resolve os relacionamentos agrupando e aninhando os veículos por cliente.
        """
        # 1. Totalizadores rápidos para o cabeçalho analítico
        total_cli_res = await self.db.execute(select(func.count(Cliente.id)))
        total_clientes = total_cli_res.scalar_one()

        total_vei_res = await self.db.execute(select(func.count(Veiculo.id)))
        total_veiculos = total_vei_res.scalar_one()

        # 2. Busca e mapeia todos os veículos vinculando os nomes dos proprietários
        query_veiculos = select(
            Veiculo.id,
            Veiculo.placa,
            Veiculo.marca,
            Veiculo.modelo,
            Veiculo.cliente_id,
            Cliente.nome.label("nome_proprietario"),
        ).join(Cliente, Veiculo.cliente_id == Cliente.id)
        res_veiculos = await self.db.execute(query_veiculos)

        # Agrupamento eficiente em memória usando defaultdict
        veiculos_por_cliente = defaultdict(list)
        for row in res_veiculos:
            dto_veiculo = VeiculoRelatorioDTO(
                id=row.id,
                placa=Placa(row.placa).formatada,
                marca=row.marca,
                modelo=row.modelo,
                nome_proprietario=row.nome_proprietario,
            )
            veiculos_por_cliente[row.cliente_id].append(dto_veiculo)

        # 3. Busca Clientes com Left Outer Join para contagem agregada de veículos
        query_clientes = (
            select(
                Cliente.id,
                Cliente.nome,
                Cliente.email,
                Cliente.telefone,
                Cliente.cpf_cnpj,
                func.count(Veiculo.id).label("total_veiculos"),
            )
            .outerjoin(Veiculo, Veiculo.cliente_id == Cliente.id)
            .group_by(
                Cliente.id,
                Cliente.nome,
                Cliente.email,
                Cliente.telefone,
                Cliente.cpf_cnpj,
            )
        )
        res_clientes = await self.db.execute(query_clientes)

        clientes_list = []
        for row in res_clientes:
            # Obtém a lista de veículos agrupada no passo anterior ou lista vazia
            veiculos_do_cliente = veiculos_por_cliente.get(row.id, [])

            dto_cliente = ClienteRelatorioDTO(
                id=row.id,
                nome=row.nome,
                email=row.email,
                telefone=Telefone(row.telefone).formatado,
                cpf_cnpj=CpfCnpj(row.cpf_cnpj).formatado,
                total_veiculos=row.total_veiculos,
                veiculos=veiculos_do_cliente,
            )
            clientes_list.append(dto_cliente)

        return RelatorioClienteVeiculoResponse(
            total_clientes=total_clientes,
            total_veiculos=total_veiculos,
            clientes=clientes_list,
        )
