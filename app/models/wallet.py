import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from . import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True
    )
    address = Column(String, nullable=False, unique=True, index=True)
    chain_id = Column(String, nullable=False, default="137")  # Polygon
    token_address = Column(String, nullable=False)  # USDC contract address
    created_at = Column(DateTime, default=utcnow, nullable=False)

    # Relationships
    agent = relationship("Agent", back_populates="wallets")

    def __repr__(self) -> str:
        return f"<Wallet(address='{self.address}', agent={self.agent_id})>"
