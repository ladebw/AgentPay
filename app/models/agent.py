import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from . import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Agent(Base):
    __tablename__ = "agents"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    api_key_hash = Column(String, nullable=False, unique=True, index=True)
    wallet_address = Column(String, nullable=False, unique=True, index=True)
    permissions = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    # Relationships
    wallets = relationship(
        "Wallet", back_populates="agent", cascade="all, delete-orphan"
    )
    invoices_sent = relationship(
        "Invoice", foreign_keys="Invoice.from_agent_id", back_populates="from_agent"
    )
    invoices_received = relationship(
        "Invoice", foreign_keys="Invoice.to_agent_id", back_populates="to_agent"
    )
    payments_sent = relationship(
        "Payment", foreign_keys="Payment.from_agent_id", back_populates="from_agent"
    )
    payments_received = relationship(
        "Payment", foreign_keys="Payment.to_agent_id", back_populates="to_agent"
    )
    webhooks = relationship(
        "Webhook", back_populates="agent", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Agent(id={self.id}, name='{self.name}', wallet='{self.wallet_address}')>"
        )
