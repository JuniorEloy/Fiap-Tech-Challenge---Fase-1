from enum import Enum
from uuid import UUID
from uuid6 import uuid7
from sqlalchemy import String, Uuid, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.shared.models.base import Base


class TipoPessoa(str, Enum):
    FISICA = "FISICA"
    JURIDICA = "JURIDICA"


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    telefone: Mapped[str] = mapped_column(String(20), nullable=False)
    cpf_cnpj: Mapped[str] = mapped_column(
        String(14), unique=True, nullable=False, index=True
    )
    tipo_pessoa: Mapped[TipoPessoa] = mapped_column(
        SQLEnum(TipoPessoa, native_enum=False), nullable=False
    )
    usuario_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=False
    )
