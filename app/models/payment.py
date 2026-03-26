import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from . import Base


def utcnow():
    return datetime.now(timezone.utc)


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(PG_UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False, index=True)
    from_agent_id = Column(PG_UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    to_agent_id = Column(PG_UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    amount = Column(Numeric(18, 6), nullable=False)
    transaction_hash = Column(String, unique=True, index=True)
    block_number = Column(Integer, nullable=True)
    gas_used = Column(Integer, nullable=True)
    gas_price_gwei = Column(Numeric(18, 9), nullable=True)
    sponsored = Column(Boolean, default=False)
    sponsor_transaction_hash = Column(String, nullable=True)
    sponsor_gas_used = Column(Integer, nullable=True)
    sponsor_gas_cost_usd = Column(Numeric(18, 6), nullable=True)
    status = Column(String, nullable=False, default=PaymentStatus.PENDING, index=True)
    error_message = Column(String, nullable=True)
    idempotency_key = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    invoice = relationship("Invoice", back_populates="payments")
    from_agent = relationship("Agent", foreign_keys=[from_agent_id], back_populates="payments_sent")
    to_agent = relationship("Agent", foreign_keys=[to_agent_id], back_populates="payments_received")
    blockchain_transaction = relationship("BlockchainTransaction", uselist=False, back_populates="payment")

    def __repr__(self):
        return f"<Payment(id={self.id}, amount={self.amount}, status='{self.status}')>"