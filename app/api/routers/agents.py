from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.schemas.agent import AgentCreate, AgentResponse, AgentWithApiKey, AgentUpdate
from app.services.agent import AgentService

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/", response_model=AgentWithApiKey, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_create: AgentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new agent with API key and wallet."""
    service = AgentService(db)
    result = await service.create_agent(
        name=agent_create.name,
        permissions=agent_create.permissions
    )
    return AgentWithApiKey(
        id=result["agent"].id,
        name=result["agent"].name,
        wallet_address=result["agent"].wallet_address,
        permissions=result["agent"].permissions,
        created_at=result["agent"].created_at,
        api_key=result["api_key"]
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get agent details."""
    service = AgentService(db)
    agent = await service.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    agent_update: AgentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update agent permissions."""
    service = AgentService(db)
    agent = await service.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    update_data = agent_update.dict(exclude_unset=True)
    if "permissions" in update_data:
        agent = await service.update_permissions(agent_id, update_data["permissions"])
    if "name" in update_data:
        agent.name = update_data["name"]
        await db.commit()
    
    return agent


@router.get("/", response_model=List[AgentResponse])
async def list_agents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all agents."""
    service = AgentService(db)
    return await service.list(skip=skip, limit=limit)