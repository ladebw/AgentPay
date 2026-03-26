import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from . import Base


def utcnow():
    return datetime.now(timezone.utc)


class WebhookStatus(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True
    )
    url = Column(String, nullable=False)
    event_types = Column(JSON, nullable=False)  # List of event types
    secret = Column(String, nullable=False)  # Signing secret
    status = Column(String, nullable=False, default=WebhookStatus.PENDING, index=True)
    delivery_attempts = Column(Integer, default=0)
    last_delivery_at = Column(DateTime, nullable=True)
    last_error = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    agent = relationship("Agent", back_populates="webhooks")

    def __repr__(self):
        return f"<Webhook(id={self.id}, url='{self.url}', status='{self.status}')>"
