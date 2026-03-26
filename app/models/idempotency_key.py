import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from . import Base


def utcnow():
    return datetime.now(timezone.utc)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String, nullable=False, unique=True, index=True)
    agent_id = Column(PG_UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    request_path = Column(String, nullable=False)
    request_hash = Column(String, nullable=False)  # hash of request body
    response_status_code = Column(Integer, nullable=True)
    response_body = Column(JSON, nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    # Relationships
    agent = relationship("Agent")

    def __repr__(self):
        return f"<IdempotencyKey(key='{self.key}', agent={self.agent_id})>"