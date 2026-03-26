from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.agent import AgentService

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_agent(
    api_key: str = Depends(api_key_header), db: AsyncSession = Depends(get_db)
):
    """Dependency to get current authenticated agent."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key missing",
        )

    service = AgentService(db)
    agent = await service.authenticate(api_key)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return agent


async def require_permission(permission: str, agent=Depends(get_current_agent)):
    """Check if agent has required permission."""
    if permission not in agent.permissions.get("allow", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{permission}' required",
        )
    return agent
