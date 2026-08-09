from fastapi import APIRouter

from app.features.estoque.cadastrar_peca_insumo.router import (
    router as cadastrar_peca_insumo_router,
)
from app.features.estoque.baixar_estoque.router import (
    router as baixar_estoque_router,
)
from app.features.estoque.registrar_entrada.router import (
    router as registrar_entrada_router,
)


estoque_router = APIRouter()

# Inclui os sub-routers de cada slice de autenticação
estoque_router.include_router(cadastrar_peca_insumo_router)
estoque_router.include_router(baixar_estoque_router)
estoque_router.include_router(registrar_entrada_router)
