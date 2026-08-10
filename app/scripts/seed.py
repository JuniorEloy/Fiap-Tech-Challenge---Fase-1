# seed_db-v2.py
"""
Script de Seed para o Banco de Dados da Oficina (Tech Challenge - Fase 1) - v2.
Popula as tabelas cadastrais base: Usuários (Operadores), Clientes, Veículos, 
Catálogo de Peças (Estoque) e Catálogo de Serviços (Mão de Obra).

Esta versão v2 corrige a validação de CPF e CNPJ inserindo dados matematicamente válidos,
suporta a propriedade de senha simplificada 'senha' (ou 'senha_hash') e integra a
propriedade de domínio 'tipo_pessoa' para os Clientes.
"""
import sys
from pathlib import Path

# Adiciona a raiz do projeto ao sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import asyncio
from decimal import Decimal
from uuid import UUID

from app.shared.infra.db.database import Base, engine, AsyncSession
from app.shared.security.password import gerar_hash_senha
from app.features.usuarios.models import Usuario
from app.features.clientes.models import Cliente
from app.features.veiculos.models import Veiculo
from app.features.estoque.models import PecaInsumo
from app.features.servicos.models import ServicoBase
from app.shared.security.roles import Role
from app.features.autenticacao.models import RefreshTokenSession


async def semear_banco():
    print("🚀 [v2] Iniciando processo de seeding com CPFs e CNPJ 100% válidos...")
    
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
                    "role": Role.RECEPCIONISTA if hasattr(Role, "RECEPCIONISTA") else "RECEPCIONISTA",
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
                    "role": Role.ESTOQUISTA if hasattr(Role, "ESTOQUISTA") else "ESTOQUISTA",
                }
            ]
            
            for op_data in operadores_dados:
                from sqlalchemy import select
                stmt = select(Usuario).where(Usuario.email == op_data["email"])
                res = await session.execute(stmt)
                if not res.scalar_one_or_none():
                    # Compatibilidade dinâmica: usa 'senha' ou 'senha_hash' dependendo da classe
                    op_params = {
                        "nome": op_data["nome"],
                        "email": op_data["email"],
                        "role": op_data["role"],
                        "ativo": True
                    }
                    if hasattr(Usuario, "senha"):
                        op_params["senha"] = op_data["hashed_senha"]
                    elif hasattr(Usuario, "senha_hash"):
                        op_params["senha_hash"] = op_data["hashed_senha"]
                    else:
                        op_params["senha"] = op_data["hashed_senha"]
                        
                    novo_op = Usuario(**op_params)
                    session.add(novo_op)
                    print(f"   ✔️ Operador adicionado: {op_data['nome']} ({op_data['role']})")
                else:
                    print(f"   ⚠️ Operador já cadastrado: {op_data['email']}")
            
            await session.flush()  # Garante IDs persistidos temporariamente
            
            # Recupera IDs de usuários criados para sincronizações se necessário
            res_gerente = await session.execute(select(Usuario).where(Usuario.email == "armando.gerente@oficina.com"))
            gerente = res_gerente.scalar_one()

            res_recepcionista = await session.execute(select(Usuario).where(Usuario.email == "barbara.recepcao@oficina.com"))
            recep = res_recepcionista.scalar_one()

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
                    "usuario_id": recep.id
                },
                {
                    "nome": "Marcos Lima",
                    "email": "marcos.lima@yahoo.com",
                    "telefone": "11977776666",
                    "cpf_cnpj": "75815318647",
                    "tipo_pessoa": "FISICA",
                    "usuario_id": recep.id
                },
                {
                    "nome": "Auto Locadora RentCar",
                    "email": "contato@rentcar.com.br",
                    "telefone": "1133334444",
                    "cpf_cnpj": "31305442000170",
                    "tipo_pessoa": "JURIDICA",
                    "usuario_id": gerente.id
                }
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
                        "usuario_id": cli_data["usuario_id"]
                    }
                    if hasattr(Cliente, "tipo_pessoa") or "tipo_pessoa" in Cliente.__table__.columns:
                        cli_params["tipo_pessoa"] = cli_data["tipo_pessoa"]
                        
                    cli_db = Cliente(**cli_params)
                    session.add(cli_db)
                    print(f"   ✔️ Cliente adicionado: {cli_db.nome} ({cli_data['tipo_pessoa']})")
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
                    "cliente_cnpj_cpf": "65564096851"
                },
                {
                    "placa": "XYZ9H87",
                    "marca": "Toyota",
                    "modelo": "Corolla 2.0 XEi",
                    "ano": 2021,
                    "cliente_cnpj_cpf": "75815318647"
                },
                {
                    "placa": "MNO4A56",
                    "marca": "Fiat",
                    "modelo": "Uno Mille 1.0",
                    "ano": 2013,
                    "cliente_cnpj_cpf": "31305442000170"
                }
            ]
            
            for vei in veiculos_dados:
                stmt = select(Veiculo).where(Veiculo.placa == vei["placa"])
                res = await session.execute(stmt)
                if not res.scalar_one_or_none():
                    proprietario = clientes_dict[vei["cliente_cnpj_cpf"]]
                    
                    novo_veiculo = Veiculo(
                        placa=vei["placa"],
                        marca=vei["marca"],
                        modelo=vei["modelo"],
                        ano=vei["ano"] if hasattr(Veiculo, "ano") else None,
                        cliente_id=proprietario.id
                    )
                    session.add(novo_veiculo)
                    print(f"   ✔️ Veículo cadastrado: {novo_veiculo.marca} {novo_veiculo.modelo} ({novo_veiculo.placa})")
                else:
                    print(f"   ⚠️ Veículo com placa {vei['placa']} já existe no cadastro.")
            
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
                    "limite_minimo": 15
                },
                {
                    "nome": "Filtro de Óleo Fram PH5317",
                    "descricao": "Filtro blindado de óleo lubrificante",
                    "preco_custo": Decimal("15.00"),
                    "preco_venda": Decimal("35.00"),
                    "quantidade_em_estoque": 18,
                    "limite_minimo": 10
                },
                {
                    "nome": "Pastilha de Freio Dianteira Bosch",
                    "descricao": "Pastilha de cerâmica macia livre de ruídos",
                    "preco_custo": Decimal("80.00"),
                    "preco_venda": Decimal("160.00"),
                    "quantidade_em_estoque": 12,  # 👈 Abaixo de 15, gatilha precisa_recompra!
                    "limite_minimo": 15
                },
                {
                    "nome": "Filtro de Ar de Cabine Tecfil",
                    "descricao": "Filtro anti-pólen para sistema de ar-condicionado",
                    "preco_custo": Decimal("20.00"),
                    "preco_venda": Decimal("45.00"),
                    "quantidade_em_estoque": 8,   # 👈 Abaixo de 15, gatilha precisa_recompra!
                    "limite_minimo": 15
                }
            ]
            
            for pec in pecas_dados:
                stmt = select(PecaInsumo).where(PecaInsumo.nome == pec["nome"])
                res = await session.execute(stmt)
                if not res.scalar_one_or_none():
                    # Compatibilidade de atributos dependendo do modelo do usuário
                    nova_peca = PecaInsumo(
                        nome=pec["nome"],
                        descricao=pec["descricao"],
                        preco_custo=pec["preco_custo"],
                        preco_venda=pec["preco_venda"],
                        quantidade_em_estoque=pec["quantidade_em_estoque"],
                        limite_minimo=pec["limite_minimo"]
                    )
                    session.add(nova_peca)
                    print(f"   ✔️ Peça catalogada: {nova_peca.nome} (Qtd: {nova_peca.quantidade_em_estoque})")
                else:
                    print(f"   ⚠️ Peça '{pec['nome']}' já catalogada no estoque.")
            
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
                    "duracao_estimada_minutos": 20
                },
                {
                    "nome": "Alinhamento e Balanceamento 3D",
                    "descricao": "Regulagem computadorizada de suspensão e balanceamento dinâmico de rodas",
                    "preco_mao_de_obra": Decimal("120.00"),
                    "duracao_estimada_minutos": 45
                },
                {
                    "nome": "Diagnóstico Completo por Scanner OBD2",
                    "descricao": "Varredura geral preventiva e corretiva de sensores de injeção eletrônica",
                    "preco_mao_de_obra": Decimal("150.00"),
                    "duracao_estimada_minutos": 30
                },
                {
                    "nome": "Troca de Pastilhas de Freio Dianteiras",
                    "descricao": "Instalação física de novos elementos de fricção e lubrificação de guias",
                    "preco_mao_de_obra": Decimal("100.00"),
                    "duracao_estimada_minutos": 40
                }
            ]
            
            for ser in servicos_dados:
                stmt = select(ServicoBase).where(ServicoBase.nome == ser["nome"])
                res = await session.execute(stmt)
                if not res.scalar_one_or_none():
                    novo_servico = ServicoBase(
                        nome=ser["nome"],
                        descricao=ser["descricao"],
                        preco_mao_de_obra=ser["preco_mao_de_obra"],
                        duracao_estimada_minutos=ser["duracao_estimada_minutos"],
                        ativo=True
                    )
                    session.add(novo_servico)
                    print(f"   ✔️ Serviço catalogado: {novo_servico.nome} (R$ {novo_servico.preco_mao_de_obra})")
                else:
                    print(f"   ⚠️ Serviço '{ser['nome']}' já catalogado.")

    print("\n🏁 Processo de Seeding [v2] finalizado com absoluto sucesso! O banco está pronto para uso e testes.")


if __name__ == "__main__":
    asyncio.run(semear_banco())
