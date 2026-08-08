from fastapi import APIRouter

from app.features.estoque.cadastrar_peca_insumo.router import (
    router as cadastrar_peca_insumo_router,
)


estoque_router = APIRouter()

# Inclui os sub-routers de cada slice de autenticação
estoque_router.include_router(cadastrar_peca_insumo_router)
