# seed_db-v3.py
"""
Script de Seed para o Banco de Dados da Oficina (Tech Challenge - Fase 1) - v3.
Popula as tabelas cadastrais base: Usuários (Operadores), Clientes, Veículos,
Catálogo de Peças (Estoque) e Catálogo de Serviços (Mão de Obra).

E agora também povoa fluxos completos de Ordens de Serviço (OSs) - normais e expressas -
com histórico de transições de status (os_status_logs) e itens vinculados.
Isso fornece massa realista para os relatórios analíticos de BI (lead times e gargalos).
"""

# seed_db-v3.py
"""
Script de Seed para o Banco de Dados da Oficina (Tech Challenge - Fase 1) - v3.
Popula as tabelas cadastrais base: Usuários (Operadores), Clientes, Veículos, 
Catálogo de Peças (Estoque) e Catálogo de Serviços (Mão de Obra).

E agora também povoa fluxos completos de Ordens de Serviço (OSs) - normais e expressas -
com histórico de transições de status (os_status_logs) e itens vinculados.
Isso fornece massa realista para os relatórios analíticos de BI (lead times e gargalos).
"""

import sys
from pathlib import Path

# Adiciona a raiz do projeto ao sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import asyncio
from decimal import Decimal
from uuid import UUID
from datetime import timedelta, datetime
from uuid import uuid7


from app.shared.infra.db.database import Base, engine, AsyncSession
from app.shared.security.password import gerar_hash_senha
from app.features.usuarios.models import Usuario
from app.features.clientes.models import Cliente
from app.features.veiculos.models import Veiculo
from app.features.estoque.models import PecaInsumo
from app.features.servicos.models import ServicoBase
from app.shared.security.roles import Role
from app.features.autenticacao.models import RefreshTokenSession
from app.features.ordens_servico.models import (
    OrdemServico,
    StatusOS,
    OrdemServicoStatusLog,
    ItemServicoOS,
    ItemPecaOS,
)


async def semear_banco():
    print(
        "🚀 [v3] Iniciando processo de seeding com CPFs, CNPJ e fluxos completos de OSs..."
    )

    async with AsyncSession(engine) as session:
        async with session.begin():
            # ==========================================
            # 1. POPULANDO OPERADORES DA OFICINA
            # ==========================================
            print("\n👤 Cadastro de Operadores Administrativos e Técnicos...")

            # Senhas limpas e hash de segurança
            hashed_gerente = gerar_hash_senha("Gerente123!")
            hashed_recep = gerar_hash_senha("Recepcao123!")
            hashed_mecanico = gerar_hash_senha("Mecanico123!")
            hashed_estoque = gerar_hash_senha("Estoque123!")

            operadores_dados = [
                {
                    "nome": "Armando Neto",
                    "email": "armando.gerente@oficina.com",
                    "hashed_senha": hashed_gerente,
                    "role": Role.GERENTE if hasattr(Role, "GERENTE") else "GERENTE",
                },
                {
                    "nome": "Barbara Silva",
                    "email": "barbara.recepcao@oficina.com",
                    "hashed_senha": hashed_recep,
                    "role": Role.RECEPCIONISTA
                    if hasattr(Role, "RECEPCIONISTA")
                    else "RECEPCIONISTA",
                },
                {
                    "nome": "Roberto Santos",
                    "email": "roberto.mecanico@oficina.com",
                    "hashed_senha": hashed_mecanico,
                    "role": Role.MECANICO if hasattr(Role, "MECANICO") else "MECANICO",
                },
                {
                    "nome": "Denilson Souza",
                    "email": "denilson.estoque@oficina.com",
                    "hashed_senha": hashed_estoque,
                    "role": Role.ESTOQUISTA
                    if hasattr(Role, "ESTOQUISTA")
                    else "ESTOQUISTA",
                },
            ]

            operadores_dict = {}
            for op_data in operadores_dados:
                from sqlalchemy import select

                stmt = select(Usuario).where(Usuario.email == op_data["email"])
                res = await session.execute(stmt)
                op_db = res.scalar_one_or_none()
                if not op_db:
                    # Compatibilidade dinâmica: usa 'senha' ou 'senha_hash' dependendo da classe
                    op_params = {
                        "nome": op_data["nome"],
                        "email": op_data["email"],
                        "role": op_data["role"],
                        "ativo": True,
                    }
                    if hasattr(Usuario, "senha"):
                        op_params["senha"] = op_data["hashed_senha"]
                    elif hasattr(Usuario, "senha_hash"):
                        op_params["senha_hash"] = op_data["hashed_senha"]
                    else:
                        op_params["senha"] = op_data["hashed_senha"]

                    op_db = Usuario(**op_params)
                    session.add(op_db)
                    print(
                        f"   ✔️ Operador adicionado: {op_data['nome']} ({op_data['role']})"
                    )
                else:
                    print(f"   ⚠️ Operador já cadastrado: {op_data['email']}")

                operadores_dict[op_data["email"]] = op_db

            await session.flush()  # Garante IDs persistidos temporariamente

            gerente = operadores_dict["armando.gerente@oficina.com"]
            recep = operadores_dict["barbara.recepcao@oficina.com"]
            mecanico = operadores_dict["roberto.mecanico@oficina.com"]

            # ==========================================
            # 2. POPULANDO CLIENTES (COM CPFS/CNPJ MATEMATICAMENTE VÁLIDOS)
            # ==========================================
            print("\n👥 Cadastro de Clientes (Pessoas Físicas e Jurídicas)...")

            # Carla Souza: CPF '65564096851' (Válido)
            # Marcos Lima: CPF '75815318647' (Válido)
            # Auto Locadora RentCar: CNPJ '31305442000170' (Válido)
            clientes_dados = [
                {
                    "nome": "Carla Souza",
                    "email": "carla.souza@gmail.com",
                    "telefone": "11988887777",
                    "cpf_cnpj": "65564096851",
                    "tipo_pessoa": "FISICA",
                    "usuario_id": recep.id,
                },
                {
                    "nome": "Marcos Lima",
                    "email": "marcos.lima@yahoo.com",
                    "telefone": "11977776666",
                    "cpf_cnpj": "75815318647",
                    "tipo_pessoa": "FISICA",
                    "usuario_id": recep.id,
                },
                {
                    "nome": "Auto Locadora RentCar",
                    "email": "contato@rentcar.com.br",
                    "telefone": "1133334444",
                    "cpf_cnpj": "31305442000170",
                    "tipo_pessoa": "JURIDICA",
                    "usuario_id": gerente.id,
                },
            ]

            clientes_dict = {}
            for cli_data in clientes_dados:
                stmt = select(Cliente).where(Cliente.cpf_cnpj == cli_data["cpf_cnpj"])
                res = await session.execute(stmt)
                cli_db = res.scalar_one_or_none()

                if not cli_db:
                    # Compatibilidade dinâmica para 'tipo_pessoa'
                    cli_params = {
                        "nome": cli_data["nome"],
                        "email": cli_data["email"],
                        "telefone": cli_data["telefone"],
                        "cpf_cnpj": cli_data["cpf_cnpj"],
                        "usuario_id": cli_data["usuario_id"],
                    }
                    if (
                        hasattr(Cliente, "tipo_pessoa")
                        or "tipo_pessoa" in Cliente.__table__.columns
                    ):
                        cli_params["tipo_pessoa"] = cli_data["tipo_pessoa"]

                    cli_db = Cliente(**cli_params)
                    session.add(cli_db)
                    print(
                        f"   ✔️ Cliente adicionado: {cli_db.nome} ({cli_data['tipo_pessoa']})"
                    )
                else:
                    print(f"   ⚠️ Cliente já cadastrado: {cli_data['nome']}")

                clientes_dict[cli_data["cpf_cnpj"]] = cli_db

            await session.flush()

            # ==========================================
            # 3. POPULANDO VEÍCULOS
            # ==========================================
            print("\n🚗 Cadastro da Frota de Veículos...")

            veiculos_dados = [
                {
                    "placa": "ABC1D23",
                    "marca": "Chevrolet",
                    "modelo": "Onix 1.0 LT Turbo",
                    "ano": 2022,
                    "cliente_cnpj_cpf": "65564096851",
                },
                {
                    "placa": "XYZ9H87",
                    "marca": "Toyota",
                    "modelo": "Corolla 2.0 XEi",
                    "ano": 2021,
                    "cliente_cnpj_cpf": "75815318647",
                },
                {
                    "placa": "MNO4A56",
                    "marca": "Fiat",
                    "modelo": "Uno Mille 1.0",
                    "ano": 2013,
                    "cliente_cnpj_cpf": "31305442000170",
                },
            ]

            veiculos_dict = {}
            for vei in veiculos_dados:
                stmt = select(Veiculo).where(Veiculo.placa == vei["placa"])
                res = await session.execute(stmt)
                vei_db = res.scalar_one_or_none()
                if not vei_db:
                    proprietario = clientes_dict[vei["cliente_cnpj_cpf"]]

                    vei_db = Veiculo(
                        placa=vei["placa"],
                        marca=vei["marca"],
                        modelo=vei["modelo"],
                        ano=vei["ano"] if hasattr(Veiculo, "ano") else None,
                        cliente_id=proprietario.id,
                    )
                    session.add(vei_db)
                    print(
                        f"   ✔️ Veículo cadastrado: {vei_db.marca} {vei_db.modelo} ({vei_db.placa})"
                    )
                else:
                    print(
                        f"   ⚠️ Veículo com placa {vei['placa']} já existe no cadastro."
                    )

                veiculos_dict[vei["placa"]] = vei_db

            await session.flush()

            # ==========================================
            # 4. POPULANDO INVENTÁRIO (PEÇAS E INSUMOS)
            # ==========================================
            print("\n📦 Alocação de Inventário de Peças e Insumos...")

            pecas_dados = [
                {
                    "nome": "Óleo de Motor Castrol Edge 5W30",
                    "descricao": "Óleo sintético premium de alta performance",
                    "preco_custo": Decimal("40.00"),
                    "preco_venda": Decimal("75.00"),
                    "quantidade_em_estoque": 25,
                    "limite_minimo": 15,
                },
                {
                    "nome": "Filtro de Óleo Fram PH5317",
                    "descricao": "Filtro blindado de óleo lubrificante",
                    "preco_custo": Decimal("15.00"),
                    "preco_venda": Decimal("35.00"),
                    "quantidade_em_estoque": 18,
                    "limite_minimo": 10,
                },
                {
                    "nome": "Pastilha de Freio Dianteira Bosch",
                    "descricao": "Pastilha de cerâmica macia livre de ruídos",
                    "preco_custo": Decimal("80.00"),
                    "preco_venda": Decimal("160.00"),
                    "quantidade_em_estoque": 12,
                    "limite_minimo": 15,
                },
                {
                    "nome": "Filtro de Ar de Cabine Tecfil",
                    "descricao": "Filtro anti-pólen para sistema de ar-condicionado",
                    "preco_custo": Decimal("20.00"),
                    "preco_venda": Decimal("45.00"),
                    "quantidade_em_estoque": 8,
                    "limite_minimo": 15,
                },
            ]

            pecas_dict = {}
            for pec in pecas_dados:
                stmt = select(PecaInsumo).where(PecaInsumo.nome == pec["nome"])
                res = await session.execute(stmt)
                peca_db = res.scalar_one_or_none()
                if not peca_db:
                    peca_db = PecaInsumo(
                        nome=pec["nome"],
                        descricao=pec["descricao"],
                        preco_custo=pec["preco_custo"],
                        preco_venda=pec["preco_venda"],
                        quantidade_em_estoque=pec["quantidade_em_estoque"],
                        limite_minimo=pec["limite_minimo"],
                    )
                    session.add(peca_db)
                    print(
                        f"   ✔️ Peça catalogada: {peca_db.nome} (Qtd: {peca_db.quantidade_em_estoque})"
                    )
                else:
                    print(f"   ⚠️ Peça '{pec['nome']}' já catalogada no estoque.")

                pecas_dict[pec["nome"]] = peca_db

            await session.flush()

            # ==========================================
            # 5. POPULANDO CATÁLOGO DE SERVIÇOS (MÃO DE OBRA)
            # ==========================================
            print("\n🛠️ Cadastro do Catálogo de Serviços e Mão de Obra...")

            servicos_dados = [
                {
                    "nome": "Troca de Óleo e Filtros",
                    "descricao": "Substituição completa do lubrificante e do filtro correspondente",
                    "preco_mao_de_obra": Decimal("60.00"),
                    "duracao_estimada_minutos": 20,
                },
                {
                    "nome": "Alinhamento e Balanceamento 3D",
                    "descricao": "Regulagem computadorizada de suspensão e balanceamento dinâmico de rodas",
                    "preco_mao_de_obra": Decimal("120.00"),
                    "duracao_estimada_minutos": 45,
                },
                {
                    "nome": "Diagnóstico Completo por Scanner OBD2",
                    "descricao": "Varredura geral preventiva e corretiva de sensores de injeção eletrônica",
                    "preco_mao_de_obra": Decimal("150.00"),
                    "duracao_estimada_minutos": 30,
                },
                {
                    "nome": "Troca de Pastilhas de Freio Dianteiras",
                    "descricao": "Instalação física de novos elementos de fricção e lubrificação de guias",
                    "preco_mao_de_obra": Decimal("100.00"),
                    "duracao_estimada_minutos": 40,
                },
            ]

            servicos_dict = {}
            for ser in servicos_dados:
                stmt = select(ServicoBase).where(ServicoBase.nome == ser["nome"])
                res = await session.execute(stmt)
                servico_db = res.scalar_one_or_none()
                if not servico_db:
                    # Garante que permite_servico_expresso seja True para o serviço rápido
                    permite_expresso = ser["nome"] in [
                        "Troca de Óleo e Filtros",
                        "Alinhamento e Balanceamento 3D",
                    ]

                    novo_servico = ServicoBase(
                        nome=ser["nome"],
                        descricao=ser["descricao"],
                        preco_mao_de_obra=ser["preco_mao_de_obra"],
                        duracao_estimada_minutos=ser["duracao_estimada_minutos"],
                        ativo=True,
                    )
                    # Se a coluna existir dinamicamente, seta o flag de expresso
                    if hasattr(ServicoBase, "permite_servico_expresso"):
                        novo_servico.permite_servico_expresso = permite_expresso

                    session.add(novo_servico)
                    print(
                        f"   ✔️ Serviço catalogado: {novo_servico.nome} (R$ {novo_servico.preco_mao_de_obra})"
                    )
                    servico_db = novo_servico
                else:
                    print(f"   ⚠️ Serviço '{ser['nome']}' já catalogado.")

                servicos_dict[ser["nome"]] = servico_db

            await session.flush()

            # ==========================================
            # 6. POPULANDO FLUXOS DE ORDENS DE SERVIÇO (MASSAS DE BI)
            # ==========================================
            if OrdemServico is None:
                print(
                    "\n⚠️ Entidade 'OrdemServico' não encontrada para seeding de fluxos transacionais. Finalizando no modo cadastral."
                )
                return

            print(
                "\n🏎️ Cadastrando Ordens de Serviço (OSs) com Históricos de Transição..."
            )

            carla = clientes_dict["65564096851"]
            marcos_lima = clientes_dict["75815318647"]
            rentcar = clientes_dict["31305442000170"]

            onix = veiculos_dict["ABC1D23"]
            corolla = veiculos_dict["XYZ9H87"]
            uno = veiculos_dict["MNO4A56"]

            # -----------------------------------------------------
            # OS 1: Expresso (Serviço Rápido) - FINALIZADA E ENTREGUE
            # -----------------------------------------------------
            print("   📋 OS 1: Expresso (Onix) -> Finalizada e Entregue...")
            abertura_os1 = datetime.now() - timedelta(days=5, hours=2)
            os1_id = uuid7()

            os1 = OrdemServico(
                id=os1_id,
                cliente_id=carla.id,
                veiculo_id=onix.id,
                status=StatusOS.ENTREGUE,
                visualizacao_hash=uuid7(),
                data_abertura=abertura_os1,
                data_conclusao=abertura_os1 + timedelta(minutes=60),
                data_notificacao_cliente=abertura_os1 + timedelta(minutes=5),
                data_resposta_cliente=abertura_os1 + timedelta(minutes=20),
                tempo_espera_aprovacao_minutos=15,
                leadtime_full_minutos=60,
                leadtime_ativo_minutos=45,
            )
            session.add(os1)
            await session.flush()

            # Itens de Peças e Serviços para OS 1
            if ItemServicoOS and ItemPecaOS:
                os1_servico = ItemServicoOS(
                    ordem_servico_id=os1_id,
                    servico_base_id=servicos_dict["Troca de Óleo e Filtros"].id,
                    preco_aplicado=Decimal("60.00"),
                    duracao_minutos=20,
                )
                os1_peca1 = ItemPecaOS(
                    ordem_servico_id=os1_id,
                    peca_id=pecas_dict["Óleo de Motor Castrol Edge 5W30"].id,
                    quantidade=1,
                    preco_unitario_aplicado=Decimal("75.00"),
                )
                os1_peca2 = ItemPecaOS(
                    ordem_servico_id=os1_id,
                    peca_id=pecas_dict["Filtro de Óleo Fram PH5317"].id,
                    quantidade=1,
                    preco_unitario_aplicado=Decimal("35.00"),
                )
                session.add_all([os1_servico, os1_peca1, os1_peca2])

            # Histórico de Status de OS 1
            if OrdemServicoStatusLog:
                logs_os1 = [
                    # Check-in inicial (Recebida)
                    OrdemServicoStatusLog(
                        ordem_servico_id=os1_id,
                        status_anterior=None,
                        status_novo=StatusOS.RECEBIDA,
                        data_transicao=abertura_os1,
                        operador_id=recep.id,
                    ),
                    # Vai direto para Orçamento por ser Expresso (Aguardando Aprovação)
                    OrdemServicoStatusLog(
                        ordem_servico_id=os1_id,
                        status_anterior=StatusOS.RECEBIDA,
                        status_novo=StatusOS.AGUARDANDO_APROVACAO,
                        data_transicao=abertura_os1 + timedelta(minutes=5),
                        operador_id=recep.id,
                    ),
                    # Cliente aprova via link público (Operador_id = None/NULL)
                    OrdemServicoStatusLog(
                        ordem_servico_id=os1_id,
                        status_anterior=StatusOS.AGUARDANDO_APROVACAO,
                        status_novo=StatusOS.EM_EXECUCAO,
                        data_transicao=abertura_os1 + timedelta(minutes=20),
                        operador_id=None,
                    ),
                    # Execução concluída (Finalizada)
                    OrdemServicoStatusLog(
                        ordem_servico_id=os1_id,
                        status_anterior=StatusOS.EM_EXECUCAO,
                        status_novo=StatusOS.FINALIZADA,
                        data_transicao=abertura_os1 + timedelta(minutes=50),
                        operador_id=mecanico.id,
                    ),
                    # Veículo entregue e faturado (Entregue)
                    OrdemServicoStatusLog(
                        ordem_servico_id=os1_id,
                        status_anterior=StatusOS.FINALIZADA,
                        status_novo=StatusOS.ENTREGUE,
                        data_transicao=abertura_os1 + timedelta(minutes=60),
                        operador_id=recep.id,
                    ),
                ]
                session.add_all(logs_os1)

            # -----------------------------------------------------
            # OS 2: Normal (Com Diagnóstico) - EM EXECUÇÃO
            # -----------------------------------------------------
            print("   📋 OS 2: Normal (Corolla) -> Em Execução...")
            abertura_os2 = datetime.now() - timedelta(hours=5)
            os2_id = uuid7()

            os2 = OrdemServico(
                id=os2_id,
                cliente_id=marcos_lima.id,
                veiculo_id=corolla.id,
                mecanico_id=mecanico.id,
                status=StatusOS.EM_EXECUCAO,
                visualizacao_hash=uuid7(),
                data_abertura=abertura_os2,
                data_notificacao_cliente=abertura_os2 + timedelta(minutes=50),
                data_resposta_cliente=abertura_os2 + timedelta(minutes=170),
                tempo_espera_aprovacao_minutos=120,
            )
            session.add(os2)
            await session.flush()

            if ItemServicoOS and ItemPecaOS:
                os2_servico1 = ItemServicoOS(
                    ordem_servico_id=os2_id,
                    servico_base_id=servicos_dict[
                        "Diagnóstico Completo por Scanner OBD2"
                    ].id,
                    preco_aplicado=Decimal("150.00"),
                    duracao_minutos=30,
                )
                os2_servico2 = ItemServicoOS(
                    ordem_servico_id=os2_id,
                    servico_base_id=servicos_dict[
                        "Troca de Pastilhas de Freio Dianteiras"
                    ].id,
                    preco_aplicado=Decimal("100.00"),
                    duracao_minutos=40,
                )
                os2_peca = ItemPecaOS(
                    ordem_servico_id=os2_id,
                    peca_id=pecas_dict["Pastilha de Freio Dianteira Bosch"].id,
                    quantidade=1,
                    preco_unitario_aplicado=Decimal("160.00"),
                )
                session.add_all([os2_servico1, os2_servico2, os2_peca])

            if OrdemServicoStatusLog:
                logs_os2 = [
                    # Check-in inicial (Recebida)
                    OrdemServicoStatusLog(
                        ordem_servico_id=os2_id,
                        status_anterior=None,
                        status_novo=StatusOS.RECEBIDA,
                        data_transicao=abertura_os2,
                        operador_id=recep.id,
                    ),
                    # Vai para a baia técnica para diagnóstico (Em Diagnóstico)
                    OrdemServicoStatusLog(
                        ordem_servico_id=os2_id,
                        status_anterior=StatusOS.RECEBIDA,
                        status_novo=StatusOS.EM_DIAGNOSTICO,
                        data_transicao=abertura_os2 + timedelta(minutes=10),
                        operador_id=mecanico.id,
                    ),
                    # Laudo técnico finalizado e enviado (Aguardando Aprovação)
                    OrdemServicoStatusLog(
                        ordem_servico_id=os2_id,
                        status_anterior=StatusOS.EM_DIAGNOSTICO,
                        status_novo=StatusOS.AGUARDANDO_APROVACAO,
                        data_transicao=abertura_os2 + timedelta(minutes=50),
                        operador_id=mecanico.id,
                    ),
                    # Cliente aprova via portal de forma autônoma (Operador_id = None/NULL)
                    OrdemServicoStatusLog(
                        ordem_servico_id=os2_id,
                        status_anterior=StatusOS.AGUARDANDO_APROVACAO,
                        status_novo=StatusOS.EM_EXECUCAO,
                        data_transicao=abertura_os2 + timedelta(minutes=170),
                        operador_id=None,
                    ),
                ]
                session.add_all(logs_os2)

            # -----------------------------------------------------
            # OS 3: Expresso (Serviço Rápido) - REJEITADA / CANCELADA
            # -----------------------------------------------------
            print("   📋 OS 3: Expresso (Uno) -> Rejeitada e Cancelada...")
            abertura_os3 = datetime.now() - timedelta(days=2)
            os3_id = uuid7()

            os3 = OrdemServico(
                id=os3_id,
                cliente_id=rentcar.id,
                veiculo_id=uno.id,
                status=StatusOS.CANCELADA,
                visualizacao_hash=uuid7(),
                data_abertura=abertura_os3,
                data_conclusao=abertura_os3 + timedelta(minutes=195),
                data_notificacao_cliente=abertura_os3 + timedelta(minutes=15),
                data_resposta_cliente=abertura_os3 + timedelta(minutes=195),
                tempo_espera_aprovacao_minutos=180,
                leadtime_full_minutos=195,
                leadtime_ativo_minutos=15,
            )
            session.add(os3)
            await session.flush()

            if ItemServicoOS and ItemPecaOS:
                os3_servico = ItemServicoOS(
                    ordem_servico_id=os3_id,
                    servico_base_id=servicos_dict["Alinhamento e Balanceamento 3D"].id,
                    preco_aplicado=Decimal("120.00"),
                    duracao_minutos=45,
                )
                session.add(os3_servico)

            if OrdemServicoStatusLog:
                logs_os3 = [
                    # Check-in inicial (Recebida)
                    OrdemServicoStatusLog(
                        ordem_servico_id=os3_id,
                        status_anterior=None,
                        status_novo=StatusOS.RECEBIDA,
                        data_transicao=abertura_os3,
                        operador_id=recep.id,
                    ),
                    # Vai direto para Orçamento por ser Expresso (Aguardando Aprovação)
                    OrdemServicoStatusLog(
                        ordem_servico_id=os3_id,
                        status_anterior=StatusOS.RECEBIDA,
                        status_novo=StatusOS.AGUARDANDO_APROVACAO,
                        data_transicao=abertura_os3 + timedelta(minutes=15),
                        operador_id=recep.id,
                    ),
                    # Cliente recusa o orçamento e a OS é encerrada (Cancelada)
                    OrdemServicoStatusLog(
                        ordem_servico_id=os3_id,
                        status_anterior=StatusOS.AGUARDANDO_APROVACAO,
                        status_novo=StatusOS.CANCELADA,
                        data_transicao=abertura_os3 + timedelta(minutes=195),
                        operador_id=None,
                    ),
                ]
                session.add_all(logs_os3)

            # -----------------------------------------------------
            # OS 4: Normal (Com Diagnóstico) - AGUARDANDO APROVAÇÃO (HASH ESTÁTICO)
            # -----------------------------------------------------
            print("   📋 OS 4: Normal (Onix) -> Aguardando Aprovação (Hash Ativo)...")
            abertura_os4 = datetime.now() - timedelta(hours=2)
            os4_id = uuid7()
            # Hash fixo conhecido para facilitar o mock do Swagger
            os4_hash = UUID("019f3a5b-7c10-7000-8000-000000000001")

            os4 = OrdemServico(
                id=os4_id,
                cliente_id=carla.id,
                veiculo_id=onix.id,
                mecanico_id=mecanico.id,
                status=StatusOS.AGUARDANDO_APROVACAO,
                visualizacao_hash=os4_hash,
                data_abertura=abertura_os4,
                data_notificacao_cliente=abertura_os4 + timedelta(minutes=80),
            )
            session.add(os4)
            await session.flush()

            if ItemServicoOS and ItemPecaOS:
                os4_servico = ItemServicoOS(
                    ordem_servico_id=os4_id,
                    servico_base_id=servicos_dict["Alinhamento e Balanceamento 3D"].id,
                    preco_aplicado=Decimal("120.00"),
                    duracao_minutos=45,
                )
                os4_peca = ItemPecaOS(
                    ordem_servico_id=os4_id,
                    peca_id=pecas_dict["Filtro de Ar de Cabine Tecfil"].id,
                    quantidade=1,
                    preco_unitario_aplicado=Decimal("45.00"),
                )
                session.add_all([os4_servico, os4_peca])

            if OrdemServicoStatusLog:
                logs_os4 = [
                    # Check-in inicial (Recebida)
                    OrdemServicoStatusLog(
                        ordem_servico_id=os4_id,
                        status_anterior=None,
                        status_novo=StatusOS.RECEBIDA,
                        data_transicao=abertura_os4,
                        operador_id=recep.id,
                    ),
                    # Mecânico joga em diagnóstico
                    OrdemServicoStatusLog(
                        ordem_servico_id=os4_id,
                        status_anterior=StatusOS.RECEBIDA,
                        status_novo=StatusOS.EM_DIAGNOSTICO,
                        data_transicao=abertura_os4 + timedelta(minutes=20),
                        operador_id=mecanico.id,
                    ),
                    # Finaliza diagnóstico e entra em orçamento
                    OrdemServicoStatusLog(
                        ordem_servico_id=os4_id,
                        status_anterior=StatusOS.EM_DIAGNOSTICO,
                        status_novo=StatusOS.AGUARDANDO_APROVACAO,
                        data_transicao=abertura_os4 + timedelta(minutes=80),
                        operador_id=mecanico.id,
                    ),
                ]
                session.add_all(logs_os4)

            print("   ✔️ 4 Fluxos de Ordens de Serviço populados com sucesso!")

    print(
        "\n🏁 Processo de Seeding [v3] finalizado com absoluto sucesso! O banco está pronto com massa de BI completa."
    )


if __name__ == "__main__":
    asyncio.run(semear_banco())
