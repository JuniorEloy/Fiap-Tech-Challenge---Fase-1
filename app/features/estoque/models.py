import uuid
from uuid import UUID
from decimal import Decimal
from sqlalchemy import String, Numeric, Integer, UUID as SqlUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base


class PecaInsumo(Base):
    __tablename__ = "pecas_insumos"

    id: Mapped[UUID] = mapped_column(
        SqlUUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )

    nome: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    descricao: Mapped[str] = mapped_column(String(255), nullable=True)

    quantidade_em_estoque: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    preco_venda: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    preco_custo: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Limite mínimo padrão de 15 unidades para disparar política de compra
    limite_minimo: Mapped[int] = mapped_column(Integer, nullable=False, default=15)

    def __repr__(self) -> str:
        return f"<PecaInsumo {self.nome} - Qtd: {self.quantidade_em_estoque}>"

    @property
    def precisa_recompra(self) -> bool:
        """Regra de Negócio: Avalia se o saldo está abaixo do limite de segurança [2]."""
        return self.quantidade_em_estoque < self.limite_minimo
