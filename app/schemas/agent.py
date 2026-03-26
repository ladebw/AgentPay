from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import uuid as uuid_pkg
from datetime import datetime


class AgentBase(BaseModel):
    name: str = Field(..., description="Agent name")
    permissions: Optional[Dict[str, Any]] = Field(
        default={}, description="Agent permissions"
    )


class AgentCreate(AgentBase):
    pass


class AgentResponse(AgentBase):
    id: uuid_pkg.UUID
    wallet_address: str
    created_at: datetime

    class Config:
        from_attributes = True


class AgentWithApiKey(AgentResponse):
    api_key: str = Field(..., description="API key (only shown once)")


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    permissions: Optional[Dict[str, Any]] = None
