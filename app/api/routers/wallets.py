from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.middleware.auth import get_current_agent
from app.models.agent import Agent
from app.blockchain import get_blockchain_client

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.get("/{agent_id}")
async def get_wallet(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Get wallet info and on-chain balance."""
    # Ensure agent can only access their own wallet (or admin)
    if str(
        current_agent.id
    ) != agent_id and "admin" not in current_agent.permissions.get("allow", []):
        raise HTTPException(status_code=403, detail="Forbidden")

    blockchain = get_blockchain_client()
    balance = await blockchain.get_balance(current_agent.wallet_address)
    return {
        "agent_id": agent_id,
        "wallet_address": current_agent.wallet_address,
        "balance": balance,
        "currency": "USDC",
    }


@router.post("/fund")
async def fund_wallet(
    amount: float,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Mock funding for testing (MVP only)."""
    blockchain = get_blockchain_client()
    # This is a mock operation; in real implementation, you'd need a faucet or transfer from admin.
    if isinstance(blockchain, MockBlockchainClient):
        blockchain.balances[current_agent.wallet_address] = (
            blockchain.balances.get(current_agent.wallet_address, 0.0) + amount
        )
        return {
            "message": f"Funded {amount} USDC",
            "new_balance": blockchain.balances[current_agent.wallet_address],
        }
    else:
        raise HTTPException(
            status_code=501, detail="Funding only available in mock mode"
        )
