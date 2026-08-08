import uuid
from uuid import UUID
from sqlalchemy import String, ForeignKey, UUID as SqlUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.shared.models.base import Base
from app.shared.domain.value_objects.placa import Placa


class Veiculo(Base):
    __tablename__ = "veiculos"

    id: Mapped[UUID] = mapped_column(
        SqlUUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )

    placa: Mapped[str] = mapped_column(
        String(7), unique=True, index=True, nullable=False
    )

    marca: Mapped[str] = mapped_column(String(50), nullable=False)

    modelo: Mapped[str] = mapped_column(String(50), nullable=False)

    ano: Mapped[int] = mapped_column(nullable=False)

    # Relacionamento: Todo veículo pertence a exatamente 1 cliente
    cliente_id: Mapped[UUID] = mapped_column(
        SqlUUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<Veiculo {self.marca} {self.modelo} - Placa: {self.placa_vo.formatada}>"
        )

    @property
    def placa_vo(self) -> Placa:
        """Reconstrói o Value Object a partir do dado primitivo persistido."""
        return Placa(self.placa)
