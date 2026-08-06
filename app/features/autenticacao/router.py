from fastapi import APIRouter

from app.features.autenticacao.login.router import router as login_router
from app.features.autenticacao.logout.router import router as logout_router
from app.features.autenticacao.refresh.router import router as refresh_router

auth_router = APIRouter()

# Inclui os sub-routers de cada slice de autenticação
auth_router.include_router(login_router)
auth_router.include_router(logout_router)
auth_router.include_router(refresh_router)
