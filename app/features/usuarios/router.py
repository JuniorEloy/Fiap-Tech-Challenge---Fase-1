from fastapi import APIRouter

from app.features.usuarios.editar_usuario.router import router as editar_usuario_router
from app.features.usuarios.cadastrar_usuario.router import (
    router as cadastrar_usuario_router,
)


usuario_router = APIRouter()

# Inclui os sub-routers de cada slice de autenticação
usuario_router.include_router(editar_usuario_router)
usuario_router.include_router(cadastrar_usuario_router)
