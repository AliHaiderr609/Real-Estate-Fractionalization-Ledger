"""SQLAlchemy ORM models for the RWA fractionalization ledger."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    total_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_tokens: Mapped[Decimal] = mapped_column(Numeric(28, 8), nullable=False)
    tokens_minted: Mapped[Decimal] = mapped_column(Numeric(28, 8), nullable=False, default=Decimal("0"))
    landlord_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    monthly_rent_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    lease_expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ledger_entries: Mapped[list["TokenLedger"]] = relationship(back_populates="property")
    transactions: Mapped[list["LedgerTransaction"]] = relationship(back_populates="property")


class TokenLedger(Base):
    __tablename__ = "token_ledger"
    __table_args__ = (
        UniqueConstraint("property_id", "owner_wallet", name="uq_property_owner"),
        Index("ix_token_ledger_owner_wallet", "owner_wallet"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    property_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    owner_wallet: Mapped[str] = mapped_column(String(128), nullable=False)
    token_balance: Mapped[Decimal] = mapped_column(Numeric(28, 8), nullable=False, default=Decimal("0"))
    purchase_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    property: Mapped["Property"] = relationship(back_populates="ledger_entries")


class LedgerTransaction(Base):
    """Immutable audit trail for mints, yields, and fees."""

    __tablename__ = "ledger_transactions"
    __table_args__ = (
        Index("ix_ledger_tx_owner_wallet", "owner_wallet"),
        Index("ix_ledger_tx_property_id", "property_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    property_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    owner_wallet: Mapped[str] = mapped_column(String(128), nullable=False)
    tx_type: Mapped[str] = mapped_column(String(32), nullable=False)  # mint | yield_payout | fee
    amount: Mapped[Decimal] = mapped_column(Numeric(28, 8), nullable=False)
    token_amount: Mapped[Decimal | None] = mapped_column(Numeric(28, 8), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    property: Mapped["Property"] = relationship(back_populates="transactions")
