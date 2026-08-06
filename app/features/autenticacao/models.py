from datetime import datetime
from typing import Optional
from uuid import UUID
from uuid6 import uuid7


from sqlalchemy import (
    String,
    Uuid,
    DateTime,
    ForeignKey,
    Boolean,
    func,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base
from app.shared.security.roles import Role
from app.shared.utils.clock import DateTimeProvider


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(200), unique=True, nullable=False, index=True
    )
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
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


class RefreshTokenSession(Base):
    __tablename__ = "refresh_token_sessions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    usuario_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    revogado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    substituido_por_id: Mapped[Optional[UUID]] = mapped_column(Uuid, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: DateTimeProvider().agora(),
        nullable=False,
    )

    revogado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="sessoes")
