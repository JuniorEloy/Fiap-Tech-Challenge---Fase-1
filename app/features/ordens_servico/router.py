from fastapi import APIRouter


from app.features.ordens_servico.abertura_os.router import (
    router as criar_ordem_servico
)

os_router = APIRouter()

# Inclui os sub-routers de cada slice de autenticação
os_router.include_router(criar_ordem_servico)
