from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AvitoAccount(Base):
    __tablename__ = "avito_accounts"
    __table_args__ = (
        UniqueConstraint("profile_id", name="uq_avito_accounts_profile_id"),
        UniqueConstraint("client_id", name="uq_avito_accounts_client_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    client_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    token_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown", server_default="unknown")
    last_token_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_token_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), server_default=func.now())
