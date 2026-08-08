import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_gerente_deve_conseguir_acessar_dashboard_com_sucesso(
    async_client: AsyncClient, token_gerente: str
):
    """
    Cenário: O Gerente solicita o relatório executivo de clientes e veículos.
    Resultado: 200 OK com totais e listas preenchidas.
    """
    headers = {"Authorization": f"Bearer {token_gerente}"}

    response = await async_client.get("/relatorio/cliente-veiculo", headers=headers)
    assert response.status_code == status.HTTP_200_OK

    body = response.json()
    assert "total_clientes" in body
    assert "total_veiculos" in body
    assert isinstance(body["clientes"], list)
    assert isinstance(body["veiculos"], list)


@pytest.mark.asyncio
async def test_recepcionista_nao_deve_acessar_dashboard_do_gerente(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Recepcionista tenta ler dados analíticos exclusivos do gerente.
    Resultado: 403 Forbidden (RBAC operando com sucesso).
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}

    response = await async_client.get("/relatorio/cliente-veiculo", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
