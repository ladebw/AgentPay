import hashlib
import secrets
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.agent import Agent
from app.models.wallet import Wallet
from app.blockchain import get_blockchain_client
from app.core.config import settings
from .base import BaseService


class AgentService(BaseService[Agent]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Agent)
        self.blockchain = get_blockchain_client()

    def generate_api_key(self) -> str:
        """Generate a random API key."""
        return secrets.token_urlsafe(32)

    def hash_api_key(self, api_key: str, salt: str) -> str:
        """Hash API key with salt."""
        return hashlib.sha256(f"{api_key}{salt}".encode()).hexdigest()

    async def create_agent(
        self, name: str, permissions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new agent with API key and wallet."""
        # Generate API key
        api_key = self.generate_api_key()
        api_key_hash = self.hash_api_key(api_key, settings.api_key_salt)

        # Create wallet on blockchain
        wallet_result = await self.blockchain.create_wallet()
        wallet_address = wallet_result["address"]

        # Create agent record
        agent = Agent(
            name=name,
            api_key_hash=api_key_hash,
            wallet_address=wallet_address,
            permissions=permissions or {},
        )
        self.db.add(agent)
        await self.db.flush()

        # Create wallet record
        wallet = Wallet(
            agent_id=agent.id,
            address=wallet_address,
            chain_id=str(settings.chain_id),
            token_address=settings.usdc_address,
        )
        self.db.add(wallet)
        await self.db.commit()

        return {
            "agent": agent,
            "api_key": api_key,  # only returned once
            "wallet_address": wallet_address,
        }

    async def authenticate(self, api_key: str) -> Optional[Agent]:
        """Authenticate an agent by API key."""
        api_key_hash = self.hash_api_key(api_key, settings.api_key_salt)
        stmt = select(Agent).where(Agent.api_key_hash == api_key_hash)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_agent_by_wallet(self, wallet_address: str) -> Optional[Agent]:
        """Get agent by wallet address."""
        stmt = select(Agent).where(Agent.wallet_address == wallet_address)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_permissions(
        self, agent_id: str, permissions: Dict[str, Any]
    ) -> Optional[Agent]:
        """Update agent permissions."""
        agent = await self.get(agent_id)
        if not agent:
            return None
        agent.permissions = permissions
        await self.db.commit()
        return agent
