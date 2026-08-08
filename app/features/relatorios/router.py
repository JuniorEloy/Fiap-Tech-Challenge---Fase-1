from fastapi import APIRouter

from app.features.relatorios.cliente_veiculo.router import (
    router as relatorios_cliente_veiculo_router,
)


cliente_router = APIRouter()

# Inclui os sub-routers de cada slice de autenticação
cliente_router.include_router(relatorios_cliente_veiculo_router)
