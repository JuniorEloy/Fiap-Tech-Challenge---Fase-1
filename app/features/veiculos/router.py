from fastapi import APIRouter

from app.features.veiculos.cadastrar_veiculo.router import (
    router as cadastrar_veiculo_router,
)
from app.features.veiculos.consultar_veiculo.router import (
    router as consultar_veiculo_router,
)

veiculo_router = APIRouter()

# Inclui os sub-routers de cada slice de autenticação
veiculo_router.include_router(cadastrar_veiculo_router)
veiculo_router.include_router(consultar_veiculo_router)
