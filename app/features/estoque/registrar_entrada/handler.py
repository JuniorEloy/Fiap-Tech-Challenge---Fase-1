from fastapi import HTTPException, status
from app.features.estoque.repository import EstoqueRepository
from app.features.estoque.registrar_entrada.schemas import RegistrarEntradaRequest, RegistroEntradaResponse


class RegistrarEntradaHandler:
    def __init__(self, repository: EstoqueRepository):
        self.repository = repository

    async def executar(self, command: RegistrarEntradaRequest) -> RegistroEntradaResponse:
        """
        Orquestra o reabastecimento de saldo de forma segura contra concorrência:
        1. Carrega a peça com bloqueio pessimista (FOR UPDATE).
        2. Guarda o saldo anterior para fins de retorno e auditoria.
        3. Soma a quantidade fornecida ao saldo atual.
        4. Salva no banco de dados e libera o bloqueio.
        """
        # 1. Recupera aplicando o Bloqueio Pessimista
        peca = await self.repository.buscar_por_id_com_bloqueio(command.peca_id)
        if not peca:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Peça/Insumo não encontrado no catálogo."
            )

        # 2. Registra o histórico de saldos
        saldo_anterior = peca.quantidade_em_estoque

        # 3. Realiza a adição física ao saldo
        peca.quantidade_em_estoque += command.quantidade

        # 4. Salva as alterações transacionalmente (o commit libera o lock)
        await self.repository.salvar(peca)

        return RegistroEntradaResponse(
            peca_id=peca.id,
            nome=peca.nome,
            quantidade_adicionada=command.quantidade,
            saldo_anterior=saldo_anterior,
            saldo_atual=peca.quantidade_em_estoque,
            limite_minimo=peca.limite_minimo,
            precisa_recompra=peca.precisa_recompra
        )