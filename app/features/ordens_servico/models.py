from enum import Enum
from datetime import datetime
from uuid import UUID
from typing import Optional, List
from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid7
from app.shared.models.base import Base
from decimal import Decimal
from sqlalchemy import Numeric

from app.features.estoque.models import PecaInsumo
from app.shared.utils.clock import DateTimeProvider
from app.features.servicos.models import ServicoBase

clock = DateTimeProvider()

CASCADE = "all, delete-orphan"
ORDEM_SERVICO_ID = "ordens_servico.id"


class StatusOS(str, Enum):
    """
    Representação de todo o ciclo de vida operacional de uma Ordem de Serviço (OS).
    Mapeado diretamente para strings no banco de dados.
    """

    RECEBIDA = "RECEBIDA"
    EM_DIAGNOSTICO = "EM_DIAGNOSTICO"
    AGUARDANDO_APROVACAO = "AGUARDANDO_APROVACAO"
    EM_EXECUCAO = "EM_EXECUCAO"
    FINALIZADA = "FINALIZADA"
    ENTREGUE = "ENTREGUE"
    CANCELADA = "CANCELADA"


# Matriz de transição rígida de negócio (Event Storming)
TRANSICOES_VALIDAS = {
    StatusOS.RECEBIDA: [
        StatusOS.EM_DIAGNOSTICO,
        StatusOS.AGUARDANDO_APROVACAO,  # Se for serviço expresso cadastrado, pula-se diagnóstico!
    ],
    StatusOS.EM_DIAGNOSTICO: [StatusOS.AGUARDANDO_APROVACAO, StatusOS.CANCELADA],
    StatusOS.AGUARDANDO_APROVACAO: [
        StatusOS.EM_EXECUCAO,
        StatusOS.CANCELADA,
        StatusOS.FINALIZADA,  # Se o cliente reprovar totalmente (cobrança do diagnóstico)
    ],
    StatusOS.EM_EXECUCAO: [StatusOS.FINALIZADA],
    StatusOS.FINALIZADA: [StatusOS.ENTREGUE],
    StatusOS.ENTREGUE: [],
    StatusOS.CANCELADA: [],
}


class OrdemServico(Base):
    """
    Entidade Raiz do Agregado (Aggregate Root) da Ordem de Serviço.
    Centraliza a orquestração do ciclo de vida físico do veículo na oficina e os dados de BI.
    """

    __tablename__ = "ordens_servico"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid7,
        comment="Identificador único global ordenado no tempo (UUIDv7)",
    )

    cliente_id: Mapped[UUID] = mapped_column(
        ForeignKey("clientes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Referência ao Cliente associado à OS",
    )

    veiculo_id: Mapped[UUID] = mapped_column(
        ForeignKey("veiculos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Referência ao Veículo em manutenção",
    )

    mecanico_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Referência ao Mecânico atribuído para execução/diagnóstico da OS",
    )

    status: Mapped[StatusOS] = mapped_column(
        String(30),
        nullable=False,
        default=StatusOS.RECEBIDA,
        index=True,
        comment="Status atual da OS dentro da Máquina de Estados",
    )

    # 🔒 Prevenção de IDOR: Chave secundária criptográfica e opaca gerada no check-in
    visualizacao_hash: Mapped[UUID] = mapped_column(
        nullable=False,
        default=uuid7,
        unique=True,
        comment="Hash criptográfico opaco utilizado para acompanhamento seguro pelo cliente sem expor o ID sequencial",
    )

    # ⏱️ Timestamps Operacionais (Usando DateTimeProvider)
    data_abertura: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=clock.agora,
        comment="Data e hora do check-in/abertura da OS na oficina",
    )
    data_conclusao: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Data e hora em que a OS atingiu o status FINALIZADA ou ENTREGUE",
    )

    # ⏱️ Timestamps Analíticos (Espera do Cliente)
    data_notificacao_cliente: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Data e hora em que o orçamento foi finalizado e enviado para o cliente por WhatsApp",
    )
    data_resposta_cliente: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Data e hora em que o cliente aprovou ou rejeitou o orçamento enviado",
    )

    # 📊 Campos de Desnormalização de Performance de Escrita (BI de Alta Performance)
    tempo_espera_aprovacao_minutos: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Diferença em minutos entre a notificação e a resposta do cliente (Inércia de aprovação)",
    )
    leadtime_full_minutos: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Duração bruta de permanência física do veículo no pátio (Entrada até a Entrega)",
    )
    leadtime_ativo_minutos: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Tempo em que a oficina trabalhou de fato (leadtime_full - tempo_espera_aprovacao)",
    )

    # Relacionamentos de Domínio (SQLAlchemy ORM)
    itens_servico: Mapped[List["ItemServicoOS"]] = relationship(
        "ItemServicoOS",
        back_populates="ordem_servico",
        cascade=CASCADE,
        lazy="selectin",
    )
    itens_peca: Mapped[List["ItemPecaOS"]] = relationship(
        "ItemPecaOS",
        back_populates="ordem_servico",
        cascade=CASCADE,
        lazy="selectin",
    )
    logs_status: Mapped[List["OrdemServicoStatusLog"]] = relationship(
        "OrdemServicoStatusLog",
        back_populates="ordem_servico",
        cascade=CASCADE,
        lazy="selectin",
    )

    def alterar_status(
        self, novo_status: StatusOS, operador_id: Optional[UUID] = None 
    ) -> OrdemServicoStatusLog:
        """
        Transiciona o status físico da Ordem de Serviço de forma segura,
        validando as restrições de negócio da máquina de estados.
        Retorna o objeto de log de status a ser persistido atomicamente na transação.
        """
        if novo_status == self.status:
            raise ValueError(
                f"A Ordem de Serviço já se encontra no status {novo_status.value}."
            )

        # Validação contra a matriz de transições válidas
        if novo_status not in TRANSICOES_VALIDAS[self.status]:
            raise ValueError(
                f"Transição física ilegal de status de {self.status.value} para {novo_status.value}."
            )

        status_anterior = self.status
        self.status = novo_status
        agora = clock.agora()

        # Carimbo analítico de conclusão (Se status finalizador)
        if novo_status in [StatusOS.FINALIZADA, StatusOS.ENTREGUE, StatusOS.CANCELADA]:
            self.data_conclusao = agora

            # Cálculo desnormalizado automático de KPIs
            self.leadtime_full_minutos = int(
                (self.data_conclusao - self.data_abertura).total_seconds() / 60
            )

            if self.tempo_espera_aprovacao_minutos:
                self.leadtime_ativo_minutos = (
                    self.leadtime_full_minutos - self.tempo_espera_aprovacao_minutos
                )
            else:
                self.leadtime_ativo_minutos = self.leadtime_full_minutos

        # Carimbo analítico de notificação do cliente
        if novo_status == StatusOS.AGUARDANDO_APROVACAO:
            self.data_notificacao_cliente = agora

        # Carimbo analítico de resposta do cliente (ao sair de AGUARDANDO_APROVACAO)
        if status_anterior == StatusOS.AGUARDANDO_APROVACAO and novo_status in [
            StatusOS.EM_EXECUCAO,
            StatusOS.CANCELADA,
            StatusOS.FINALIZADA,
        ]:
            self.data_resposta_cliente = agora
            if self.data_notificacao_cliente:
                self.tempo_espera_aprovacao_minutos = int(
                    (
                        self.data_resposta_cliente - self.data_notificacao_cliente
                    ).total_seconds()
                    / 60
                )

        # Retorna o log de transição gerado automaticamente usando o relógio central
        return OrdemServicoStatusLog(
            ordem_servico_id=self.id,
            status_anterior=status_anterior,
            status_novo=novo_status,
            data_transicao=agora,
            operador_id=operador_id,
        )


class ItemServicoOS(Base):
    """
    Entidade representando as Mãos de Obra atreladas a uma Ordem de Serviço específica.
    """

    __tablename__ = "os_itens_servico"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    ordem_servico_id: Mapped[UUID] = mapped_column(
        ForeignKey(ORDEM_SERVICO_ID, ondelete="CASCADE"), nullable=False, index=True
    )

    servico_base_id: Mapped[UUID] = mapped_column(
        ForeignKey("servicos_base.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    preco_aplicado: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Preço cobrado pela mão de obra no momento da execução",
    )

    duracao_minutos: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Duração real ou estimada em minutos acordada na OS",
    )

    adicionado_em: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=clock.agora,
        comment="Momento em que o serviço foi acoplado à OS",
    )

    # Relacionamentos ORM
    ordem_servico: Mapped["OrdemServico"] = relationship(
        "OrdemServico", back_populates="itens_servico"
    )
    servico_base: Mapped[ServicoBase] = relationship("ServicoBase", lazy="joined")


class ItemPecaOS(Base):
    """
    Entidade representando as Peças de Reposição alocadas na Ordem de Serviço.
    """

    __tablename__ = "os_itens_peca"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    ordem_servico_id: Mapped[UUID] = mapped_column(
        ForeignKey(ORDEM_SERVICO_ID, ondelete="CASCADE"), nullable=False, index=True
    )

    peca_id: Mapped[UUID] = mapped_column(
        ForeignKey("pecas_insumos.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    quantidade: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Quantidade física demandada do estoque",
    )

    preco_unitario_aplicado: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Preço de venda unitário congelado no momento do orçamento",
    )

    adicionado_em: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=clock.agora
    )

    # Relacionamentos ORM
    ordem_servico: Mapped["OrdemServico"] = relationship(
        "OrdemServico", back_populates="itens_peca"
    )

    peca: Mapped["PecaInsumo"] = relationship("PecaInsumo", lazy="joined")


class OrdemServicoStatusLog(Base):
    """
    Audit Log de transição física de status da Ordem de Serviço.
    """

    __tablename__ = "os_status_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    ordem_servico_id: Mapped[UUID] = mapped_column(
        ForeignKey(ORDEM_SERVICO_ID, ondelete="CASCADE"), nullable=False, index=True
    )

    status_anterior: Mapped[Optional[StatusOS]] = mapped_column(
        String(30),
        nullable=True,
        comment="Status de origem do veículo (Nulo para abertura de OS)",
    )

    status_novo: Mapped[StatusOS] = mapped_column(
        String(30), nullable=False, comment="Novo status de destino estabelecido"
    )

    data_transicao: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=clock.agora,
        comment="Timestamp preciso da transição física de estado",
    )

    operador_id: Mapped[UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Referência ao operador autenticado",
    )

    # Relacionamentos ORM
    ordem_servico: Mapped["OrdemServico"] = relationship(
        "OrdemServico", back_populates="logs_status"
    )
