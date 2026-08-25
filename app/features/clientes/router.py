from fastapi import APIRouter

from app.features.clientes.cadastrar_cliente.router import (
    router as cadastrar_cliente_router,
)
from app.features.clientes.consultar_cliente.router import (
    router as consultar_clientes_router,
)
from app.features.clientes.editar_cliente.router import (
    router as editar_cliente_router,
)
from app.features.clientes.excluir_cliente.router import (
    router as excluir_cliente_router,
)

cliente_router = APIRouter()

# Inclui os sub-routers de cada slice de autenticação
cliente_router.include_router(cadastrar_cliente_router)
cliente_router.include_router(consultar_clientes_router)
cliente_router.include_router(editar_cliente_router)
cliente_router.include_router(excluir_cliente_router)
