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
from app.shared.domain.value_objects.placa import Placa
from app.shared.domain.value_objects.email import Email
from app.shared.domain.value_objects.telefone import Telefone


class RelatorioClienteVeiculoQueryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def obter_dados_gerais(self) -> RelatorioClienteVeiculoResponse:
        """
        Recupera dados analíticos cruzando informações de clientes e veículos.
        Retorna projeções de leitura extremamente rápidas (CQRS).
        """
        # 1. Totalizadores rápidos de auditoria operacional
        total_cli_res = await self.db.execute(select(func.count(Cliente.id)))
        total_clientes = total_cli_res.scalar_one()

        total_vei_res = await self.db.execute(select(func.count(Veiculo.id)))
        total_veiculos = total_vei_res.scalar_one()

        # 2. Clientes com contagem agregada de veículos (Left Outer Join)
        # Nota: Se o seu modelo possuir o campo 'telefone', adicione-o no select
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
            clientes_list.append(
                ClienteRelatorioDTO(
                    id=row.id,
                    nome=row.nome,
                    # 🛡️ Garantindo consistência de saída com seus novos Value Objects:
                    email=Email(row.email).valor,
                    telefone=Telefone(row.telefone).formatado,  # Ex: (11) 98888-7777
                    cpf_cnpj=CpfCnpj(row.cpf_cnpj).formatado,
                    total_veiculos=row.total_veiculos,
                )
            )

        # 3. Veículos com nome do Proprietário correspondente (Inner Join)
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
                VeiculoRelatorioDTO(
                    id=row.id,
                    placa=Placa(row.placa).formatada,  # Saída limpa do VO Placa
                    marca=row.marca,
                    modelo=row.modelo,
                    nome_proprietario=row.nome_proprietario,
                )
            )

        return RelatorioClienteVeiculoResponse(
            total_clientes=total_clientes,
            total_veiculos=total_veiculos,
            clientes=clientes_list,
            veiculos=veiculos_list,
        )
