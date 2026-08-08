from datetime import datetime
from uuid import UUID
from uuid6 import uuid7
from typing import TYPE_CHECKING

from sqlalchemy import (
    String,
    Uuid,
    DateTime,
    Boolean,
    func,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base
from app.shared.security.roles import Role
from app.shared.utils.clock import DateTimeProvider

# Proteção contra importação circular
if TYPE_CHECKING:
    from app.features.autenticacao.models import RefreshTokenSession

class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    nome: Mapped[str] = mapped_column(String(150), nullable=False) # Tamanho 150
    email: Mapped[str] = mapped_column(
        String(200), unique=True, nullable=False, index=True
    )
    senha: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        SQLEnum(Role, native_enum=False), nullable=False, default=Role.CLIENTE
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: DateTimeProvider().agora(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: DateTimeProvider().agora(),
        onupdate=func.now(),
        nullable=False,
    )

    sessoes: Mapped[list["RefreshTokenSession"]] = relationship(
        "RefreshTokenSession", back_populates="usuario", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Usuario {self.email} - Role: {self.role}>"