from abc import ABC, abstractmethod
from decimal import Decimal
from uuid import UUID


class EnviadorNotificacaoPort(ABC):
    @abstractmethod
    async def enviar_link_aprovacao(
        self,
        telefone: str,
        cliente_nome: str,
        visualizacao_hash: UUID,
        valor_total: Decimal,
    ) -> bool:
        """
        Envia o link de aprovação da Ordem de Serviço via WhatsApp.
        """
        pass

    @abstractmethod
    async def enviar_notificacao_conclusao(
        self, telefone: str, cliente_nome: str, placa: str
    ) -> bool:
        """
        Envia um aviso informando que o veículo já está pronto para retirada.
        """
        pass
