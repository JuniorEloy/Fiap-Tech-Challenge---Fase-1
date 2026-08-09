from fastapi import APIRouter

from app.features.servicos.cadastrar_servico.router import (
    router as cadastrar_servico_router,
)
from app.features.servicos.consultar_servico.router import (
    router as consultar_servico_router,
)
from app.features.servicos.editar_servico.router import (
    router as editar_servico_router,
)

servico_router = APIRouter()

# Inclui os sub-routers de cada slice de autenticação
servico_router.include_router(cadastrar_servico_router)
servico_router.include_router(consultar_servico_router)
servico_router.include_router(editar_servico_router)
