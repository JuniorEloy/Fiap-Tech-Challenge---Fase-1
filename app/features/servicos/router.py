from fastapi import APIRouter

from app.features.servicos.cadastrar_servico.router import (
    router as cadastrar_servico_router,
)

servico_router = APIRouter()

# Inclui os sub-routers de cada slice de autenticação
servico_router.include_router(cadastrar_servico_router)
