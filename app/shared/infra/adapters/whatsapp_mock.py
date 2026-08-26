import logging
from decimal import Decimal
from uuid import UUID
from app.shared.domain.ports.notificacao import EnviadorNotificacaoPort

logger = logging.getLogger("mecanicar.whatsapp")


class WhatsAppConsoleAdapter(EnviadorNotificacaoPort):
    async def enviar_link_aprovacao(
        self,
        telefone: str,
        cliente_nome: str,
        visualizacao_hash: UUID,
        valor_total: Decimal,
    ) -> bool:
        link = f"http://localhost:8000/publico/orcamentos/{visualizacao_hash}"
        mensagem = (
            f"📱 [WHATSAPP OUT] Olá {cliente_nome}! O orçamento da sua manutenção "
            f"está pronto no valor de R$ {valor_total:.2f}. "
            f"Acesse o link para aprovar os serviços de forma online: {link}"
        )
        logger.info(mensagem)
        print(
            f"\n--- ENVIO DE WHATSAPP ---\nPara: {telefone}\nMsg: {mensagem}\n-------------------------\n"
        )
        return True

    async def enviar_notificacao_conclusao(
        self, telefone: str, cliente_nome: str, placa: str
    ) -> bool:
        mensagem = (
            f"📱 [WHATSAPP OUT] Ótima notícia, {cliente_nome}! Os serviços do veículo "
            f"de placa {placa} foram finalizados com sucesso. "
            f"Seu carro já está pronto para retirada no nosso pátio!"
        )
        logger.info(mensagem)
        print(
            f"\n--- ENVIO DE WHATSAPP ---\nPara: {telefone}\nMsg: {mensagem}\n-------------------------\n"
        )
        return True
