import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from . import Base


def utcnow():
    return datetime.now(timezone.utc)


class InvoiceStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_agent_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True
    )
    to_agent_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True
    )
    amount = Column(Numeric(18, 6), nullable=False)  # USDC with 6 decimal places
    currency = Column(String, nullable=False, default="USDC")
    status = Column(String, nullable=False, default=InvoiceStatus.PENDING, index=True)
    description = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    from_agent = relationship(
        "Agent", foreign_keys=[from_agent_id], back_populates="invoices_sent"
    )
    to_agent = relationship(
        "Agent", foreign_keys=[to_agent_id], back_populates="invoices_received"
    )
    payments = relationship(
        "Payment", back_populates="invoice", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Invoice(id={self.id}, amount={self.amount}, status='{self.status}')>"
