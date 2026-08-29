from fastapi import FastAPI

from app.shared.health import router as health_router
from app.features.autenticacao.router import auth_router
from app.features.clientes.router import cliente_router
from app.features.usuarios.router import usuario_router
from app.features.veiculos.router import veiculo_router
from app.features.relatorios.router import relatorio_router
from app.features.servicos.router import servico_router
from app.features.estoque.router import estoque_router
from app.features.ordens_servico.router import os_router

app = FastAPI(
    title="Mecanicar Service Integrated System",
    description="API - Gestão de Oficina Mecânica",
    version="1.0.0",
)

# Registra os routers principais da aplicação
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(cliente_router)
app.include_router(usuario_router)
app.include_router(veiculo_router)
app.include_router(relatorio_router)
app.include_router(estoque_router)
app.include_router(servico_router)
app.include_router(os_router)
