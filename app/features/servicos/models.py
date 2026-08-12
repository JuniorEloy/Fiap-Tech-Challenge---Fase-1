from uuid import UUID
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Numeric, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.shared.models.base import Base
from uuid import uuid7


class ServicoBase(Base):
    """
    Entidade de Domínio representando o Catálogo de Serviços (Mão de Obra).
    Contém a tabela de preços de referência e tempos estimados de execução.
    """

    __tablename__ = "servicos_base"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    nome: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    descricao: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, default=None
    )
    preco_mao_de_obra: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    duracao_estimada_minutos: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    permite_servico_expresso: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Flag indicando se este serviço é expresso e pula a etapa de diagnóstico físico pelo mecânico",
    )

    def __repr__(self) -> str:
        return f"<ServicoBase {self.nome} - R$ {self.preco_mao_de_obra} - {self.duracao_estimada_minutos} min>"
