import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from . import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BlockchainTransactionStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class BlockchainTransaction(Base):
    __tablename__ = "blockchain_transactions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False, index=True
    )
    hash = Column(String, unique=True, index=True)
    from_address = Column(String, nullable=False)
    to_address = Column(String, nullable=False)
    amount = Column(Numeric(18, 6), nullable=False)
    gas_used = Column(Integer, nullable=True)
    gas_price_gwei = Column(Numeric(18, 9), nullable=True)
    block_number = Column(Integer, nullable=True)
    status = Column(
        String, nullable=False, default=BlockchainTransactionStatus.PENDING, index=True
    )
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    payment = relationship("Payment", back_populates="blockchain_transaction")

    def __repr__(self) -> str:
        return f"<BlockchainTransaction(hash='{self.hash}', status='{self.status}')>"
