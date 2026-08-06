import sys
from pathlib import Path

# Adiciona a raiz do projeto ao sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import asyncio
from sqlalchemy import select
from app.shared.infra.db.database import SessionLocal as AsyncSessionLocal
from app.shared.security.roles import Role
from app.shared.security.password import gerar_hash_senha
from app.features.autenticacao.models import Usuario
from app.features.clientes.models import Cliente, TipoPessoa


async def popular_banco():
    async with AsyncSessionLocal() as db:
        # 1. Povoamento dos Operadores Internos
        operadores_iniciais = [
            {
                "nome": "Armando Gerente",
                "email": "gerente@oficina.com",
                "senha": "SenhaSegura123!",
                "role": Role.GERENTE,
            },
            {
                "nome": "Bárbara Recepcionista",
                "email": "recepcao@oficina.com",
                "senha": "SenhaSegura123!",
                "role": Role.RECEPCIONISTA,
            },
            {
                "nome": "Roberto Mecânico",
                "email": "mecanico@oficina.com",
                "senha": "SenhaSegura123!",
                "role": Role.MECANICO,
            },
            {
                "nome": "Denilson Estoquista",
                "email": "estoque@oficina.com",
                "senha": "SenhaSegura123!",
                "role": Role.ESTOQUISTA,
            },
        ]

        for op in operadores_iniciais:
            res = await db.execute(select(Usuario).where(Usuario.email == op["email"]))
            if not res.scalar_one_or_none():
                usuario = Usuario(
                    nome=op["nome"],
                    email=op["email"],
                    senha_hash=gerar_hash_senha(op["senha"]),
                    role=op["role"],
                )
                db.add(usuario)

        await db.flush()

        # 2. Clientes com CPFs e CNPJ Matematicamente Válidos 🎯
        clientes_iniciais = [
            {
                "nome": "Carlos Eduardo Andrade",
                "cpf_cnpj": "52998224725",
                "tipo_pessoa": TipoPessoa.FISICA,
                "email": "carlos.andrade@gmail.com",
                "telefone": "11987654321",
                "senha": "SenhaSegura123!",
            },
            {
                "nome": "Mariana Oliveira Silva",
                "cpf_cnpj": "82312889021",
                "tipo_pessoa": TipoPessoa.FISICA,
                "email": "mariana.silva@hotmail.com",
                "telefone": "11912345678",
                "senha": "SenhaSegura123!",
            },
            {
                "nome": "Transportadora Rápido Express LTDA",
                "cpf_cnpj": "12345678000195",
                "tipo_pessoa": TipoPessoa.JURIDICA,
                "email": "contato@rapidoexpress.com.br",
                "telefone": "1133334444",
                "senha": "SenhaSegura123!",
            },
        ]

        for c in clientes_iniciais:
            res_user = await db.execute(
                select(Usuario).where(Usuario.email == c["email"])
            )
            usuario_cliente = res_user.scalar_one_or_none()

            if not usuario_cliente:
                usuario_cliente = Usuario(
                    nome=c["nome"],
                    email=c["email"],
                    senha_hash=gerar_hash_senha(c["senha"]),
                    role=Role.CLIENTE,
                )
                db.add(usuario_cliente)
                await db.flush()

            res_cli = await db.execute(
                select(Cliente).where(Cliente.cpf_cnpj == c["cpf_cnpj"])
            )
            if not res_cli.scalar_one_or_none():
                cliente = Cliente(
                    nome=c["nome"],
                    cpf_cnpj=c["cpf_cnpj"],
                    tipo_pessoa=c["tipo_pessoa"],
                    email=c["email"],
                    telefone=c["telefone"],
                    usuario_id=usuario_cliente.id,
                )
                db.add(cliente)

        await db.commit()
        print(
            "🌱 Banco de dados povoado com operadores e clientes válidos com sucesso!"
        )


if __name__ == "__main__":
    asyncio.run(popular_banco())
