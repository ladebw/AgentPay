"""
Tests for wallet routes (happy path).
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.routers.wallets import router
from app.api.middleware.auth import get_current_agent
from app.models.agent import Agent
from app.core.database import get_db

# Create a test FastAPI app with the router
app = FastAPI()
app.include_router(router, prefix="/api/v1")

# Override dependencies
mock_session = AsyncMock(spec=AsyncSession)
async def override_get_db():
    yield mock_session

mock_agent = Agent(
    id="test-agent-id",
    name="Test Agent",
    wallet_address="0x1234567890abcdef",
    permissions={"allow": ["admin"]},
    api_key_hash="hash",
    created_at="2025-01-01T00:00:00"
)

async def override_get_current_agent():
    return mock_agent

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_agent] = override_get_current_agent

@pytest_asyncio.fixture
async def client():
    """Async test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

class TestWalletRoutes:
    """Test suite for wallet endpoints."""
    
    @pytest.fixture(autouse=True)
    def reset_mocks(self):
        """Reset mocks before each test."""
        mock_session.reset_mock()
        yield
        app.dependency_overrides.clear()
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_agent] = override_get_current_agent
    
    @pytest.mark.asyncio
    async def test_get_wallet_success(self, client):
        """Happy path: get wallet balance."""
        from app.blockchain import get_blockchain_client
        mock_blockchain = AsyncMock()
        mock_blockchain.get_balance.return_value = 1000.0
        
        with patch('app.api.routers.wallets.get_blockchain_client', return_value=mock_blockchain):
            response = await client.get("/api/v1/wallets/test-agent-id")
            
            assert response.status_code == 200
            data = response.json()
            assert data["agent_id"] == "test-agent-id"
            assert data["wallet_address"] == "0x1234567890abcdef"
            assert data["balance"] == 1000.0
            assert data["currency"] == "USDC"
            mock_blockchain.get_balance.assert_called_once_with("0x1234567890abcdef")
    
    @pytest.mark.asyncio
    async def test_fund_wallet_mock_mode(self, client):
        """Happy path: fund wallet in mock mode."""
        from app.blockchain import get_blockchain_client
        from app.blockchain.mock import MockBlockchainClient
        
        mock_blockchain = MockBlockchainClient()
        mock_blockchain.balances = {"0x1234567890abcdef": 500.0}
        
        with patch('app.api.routers.wallets.get_blockchain_client', return_value=mock_blockchain):
            response = await client.post(
                "/api/v1/wallets/fund",
                params={"amount": 100.0}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Funded 100.0 USDC"
            assert data["new_balance"] == 600.0
            assert mock_blockchain.balances["0x1234567890abcdef"] == 600.0