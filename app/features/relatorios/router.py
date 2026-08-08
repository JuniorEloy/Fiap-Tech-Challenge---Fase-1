from fastapi import APIRouter

from app.features.relatorios.cliente_veiculo.router import (
    router as relatorios_cliente_veiculo_router,
)


relatorio_router = APIRouter()

# Inclui os sub-routers de cada slice de autenticação
relatorio_router.include_router(relatorios_cliente_veiculo_router)
