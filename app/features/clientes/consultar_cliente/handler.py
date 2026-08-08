import re
from uuid import UUID
from typing import List
from fastapi import HTTPException, status
from ..repository import ClienteRepository
from .schemas import ClienteResponse
from app.shared.domain.value_objects.cpf_cnpj import CpfCnpj


class ConsultarClienteHandler:
    def __init__(self, repository: ClienteRepository):
        self.repository = repository

    async def listar_todos(self) -> List[ClienteResponse]:
        clientes = await self.repository.listar()
        return [ClienteResponse.model_validate(c) for c in clientes]

    async def buscar_por_cpf_cnpj(self, documento: str) -> ClienteResponse:
        # O Value Object valida e extrai apenas os números (seja CPF de 11 dígitos ou CNPJ de 14)
        doc = CpfCnpj(documento)

        cliente = await self.repository.buscar_por_cpf_cnpj(doc.valor)
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente com CPF/CNPJ '{doc.formatado}' não foi encontrado.",
            )
        return ClienteResponse.model_validate(cliente)

    async def buscar_por_id(self, cliente_id: UUID) -> ClienteResponse:
        cliente = await self.repository.buscar_por_id(cliente_id)
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente com ID '{cliente_id}' não foi encontrado.",
            )
        return ClienteResponse.model_validate(cliente)
