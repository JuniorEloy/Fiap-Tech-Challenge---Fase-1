# tests/integration/features/test_relatorios_api-v2.py
import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_gerente_deve_conseguir_acessar_relatorio_cliente_veiculo_com_sucesso(
    async_client: AsyncClient, token_gerente: str
):
    """
    Cenário: O Gerente solicita o relatório analítico de clientes e veículos.
    Resultado esperado: 200 OK com totais e veículos aninhados dentro de cada cliente correspondente.
    """
    headers = {"Authorization": f"Bearer {token_gerente}"}
    
    response = await async_client.get("/relatorio/cliente-veiculo", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    body = response.json()
    assert "total_clientes" in body
    assert "total_veiculos" in body
    assert isinstance(body["clientes"], list)
    
    # 🌟 A validação agora atesta que veículos estão aninhados sob cada cliente!
    assert "veiculos" not in body  # Não deve mais existir uma chave flat "veiculos" na raiz
    
    for cliente in body["clientes"]:
        assert "id" in cliente
        assert "nome" in cliente
        assert "email" in cliente
        assert "telefone" in cliente
        assert "cpf_cnpj" in cliente
        assert "total_veiculos" in cliente
        assert "veiculos" in cliente
        assert isinstance(cliente["veiculos"], list)


@pytest.mark.asyncio
async def test_recepcionista_nao_deve_acessar_relatorio_do_gerente(
    async_client: AsyncClient, token_recepcionista: str
):
    """
    Cenário: Recepcionista tenta ler o relatório analítico exclusivo de gerência.
    Resultado esperado: 403 Forbidden (Controle RBAC atuando adequadamente).
    """
    headers = {"Authorization": f"Bearer {token_recepcionista}"}
    
    response = await async_client.get("/relatorio/cliente-veiculo", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
