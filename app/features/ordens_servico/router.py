from fastapi import APIRouter

from app.features.ordens_servico.abrir.router import router as criar_ordem_servico
from app.features.ordens_servico.diagnosticar.router import router as diagnosticar_os
from app.features.ordens_servico.finalizar.router import router as finalizar_os
from app.features.ordens_servico.aprovar_orcamento.router import (
    router as aprovar_orcamento_os,
)

os_router = APIRouter()

# Inclui os sub-routers de cada slice de autenticação
os_router.include_router(criar_ordem_servico)
os_router.include_router(diagnosticar_os)
os_router.include_router(aprovar_orcamento_os)
os_router.include_router(finalizar_os)