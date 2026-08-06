from fastapi import FastAPI

from app.shared.health import router as health_router
from app.features.autenticacao.router import auth_router
from app.features.clientes.consultar_cliente.router import router as cliente_router


app = FastAPI(
    title="Automotive Service Integrated System",
    description="MVP de Gestão de Oficina Mecânica - Tech Challenge FIAP",
    version="1.0.0",
)

# Registra os routers principais da aplicação
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(cliente_router)
