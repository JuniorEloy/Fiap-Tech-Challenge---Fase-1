from fastapi import HTTPException, status
from app.features.estoque.repository import EstoqueRepository
from app.features.estoque.baixar_estoque.schemas import (
    BaixarEstoqueRequest,
    BaixaEstoqueResponse,
)


class BaixarEstoqueHandler:
    def __init__(self, repository: EstoqueRepository):
        self.repository = repository

    async def executar(self, command: BaixarEstoqueRequest) -> BaixaEstoqueResponse:
        """
        Executa a baixa física de saldo de forma segura contra concorrência:
        1. Carrega a peça com lock FOR UPDATE.
        2. Valida disponibilidade de saldo suficiente.
        3. Deduz o saldo físico do estoque.
        4. Avalia política de domínio de limite mínimo (limite de 15 itens).
        5. Atualiza o banco de dados.
        """
        # 1. Recupera aplicando Bloqueio Pessimista
        peca = await self.repository.buscar_por_id_com_bloqueio(command.peca_id)
        if not peca:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Peça/Insumo não encontrado no catálogo.",
            )

        # 2. Valida saldo suficiente
        if peca.quantidade_em_estoque < command.quantidade:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estoque insuficiente. Saldo disponível: {peca.quantidade_em_estoque} unidades.",
            )

        # 3. Realiza a dedução física do saldo
        peca.quantidade_em_estoque -= command.quantidade

        # 4. Avalia a política de recompra (Gatilho quando < limite_minimo de 15 unidades)
        precisa_recompra = peca.precisa_recompra
        if precisa_recompra:
            # 📢 Política: "Sempre quando o estoque estiver com menos de 15 itens iniciar processo de compra"
            # Aqui simularíamos o disparo do comando de compra ou inserção na tabela de solicitações.
            # Para esta entrega, o indicador é computado e retornado transacionalmente.
            pass

        # 5. Persiste as alterações e libera o lock do banco de dados (no commit)
        await self.repository.salvar(peca)

        return BaixaEstoqueResponse(
            peca_id=peca.id,
            nome=peca.nome,
            quantidade_retirada=command.quantidade,
            saldo_restante=peca.quantidade_em_estoque,
            limite_minimo=peca.limite_minimo,
            precisa_recompra=precisa_recompra,
        )
