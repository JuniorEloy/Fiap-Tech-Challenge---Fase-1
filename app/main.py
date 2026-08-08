from fastapi import FastAPI

from app.shared.health import router as health_router
from app.features.autenticacao.router import auth_router
from app.features.clientes.router import cliente_router
from app.features.usuarios.cadastrar_usuario.router import router as usuario_router
from app.features.veiculos.router import veiculo_router

app = FastAPI(
    title="Automotive Service Integrated System",
    description="MVP de Gestão de Oficina Mecânica - Tech Challenge FIAP",
    version="1.0.0",
)

# Registra os routers principais da aplicação
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(cliente_router)
app.include_router(usuario_router)
app.include_router(veiculo_router)
