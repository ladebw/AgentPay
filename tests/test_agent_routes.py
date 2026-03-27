"""
Tests for agent routes (happy path).
"""

import uuid
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.routers.agents import router
from app.services.agent import AgentService
from app.core.database import get_db

# Create a test FastAPI app with the router
app = FastAPI()
app.include_router(router, prefix="/api/v1")

# Override get_db dependency with a mock async session
mock_session = AsyncMock(spec=AsyncSession)


async def override_get_db():
    yield mock_session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def client():
    """Async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


class TestAgentRoutes:
    """Test suite for agent endpoints."""

    # Test UUID for consistent testing
    TEST_AGENT_ID = "12345678-1234-5678-1234-567812345678"

    @pytest.fixture(autouse=True)
    def reset_mocks(self):
        """Reset mocks before each test."""
        mock_session.reset_mock()
        yield
        app.dependency_overrides.clear()
        app.dependency_overrides[get_db] = override_get_db

    @pytest.mark.asyncio
    async def test_create_agent_success(self, client):
        """Happy path: create agent returns API key."""
        # Mock the agent service's create_agent method
        mock_agent = MagicMock()
        mock_agent.id = self.TEST_AGENT_ID
        mock_agent.name = "Test Agent"
        mock_agent.wallet_address = "0x123"
        mock_agent.permissions = {}
        mock_agent.created_at = "2025-01-01T00:00:00"

        with patch.object(
            AgentService, "create_agent", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = {
                "agent": mock_agent,
                "api_key": "test_api_key_123",
                "wallet_address": "0x123",
            }

            response = await client.post(
                "/api/v1/agents/", json={"name": "Test Agent", "permissions": {}}
            )

            assert response.status_code == 201
            data = response.json()
            assert data["id"] == self.TEST_AGENT_ID
            assert data["name"] == "Test Agent"
            assert data["wallet_address"] == "0x123"
            assert data["api_key"] == "test_api_key_123"
            mock_create.assert_called_once_with(name="Test Agent", permissions={})

    @pytest.mark.asyncio
    async def test_get_agent_success(self, client):
        """Happy path: retrieve agent by ID."""
        mock_agent = MagicMock()
        mock_agent.id = self.TEST_AGENT_ID
        mock_agent.name = "Test Agent"
        mock_agent.wallet_address = "0x123"
        mock_agent.permissions = {}
        mock_agent.created_at = "2025-01-01T00:00:00"

        with patch.object(AgentService, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_agent

            response = await client.get(f"/api/v1/agents/{self.TEST_AGENT_ID}")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == self.TEST_AGENT_ID
            assert data["name"] == "Test Agent"
            mock_get.assert_called_once_with(self.TEST_AGENT_ID)

    @pytest.mark.asyncio
    async def test_list_agents_success(self, client):
        """Happy path: list agents with pagination."""
        mock_agent = MagicMock()
        mock_agent.id = self.TEST_AGENT_ID
        mock_agent.name = "Test Agent"
        mock_agent.wallet_address = "0x123"
        mock_agent.permissions = {}
        mock_agent.created_at = "2025-01-01T00:00:00"

        with patch.object(AgentService, "list", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [mock_agent]

            response = await client.get("/api/v1/agents/?skip=0&limit=10")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == self.TEST_AGENT_ID
            mock_list.assert_called_once_with(skip=0, limit=10)

    @pytest.mark.asyncio
    async def test_update_agent_permissions_success(self, client):
        """Happy path: update agent permissions."""
        mock_agent = MagicMock()
        mock_agent.id = self.TEST_AGENT_ID
        mock_agent.name = "Test Agent"
        mock_agent.wallet_address = "0x123"
        mock_agent.permissions = {"allow": ["payment"]}
        mock_agent.created_at = "2025-01-01T00:00:00"

        with (
            patch.object(AgentService, "get", new_callable=AsyncMock) as mock_get,
            patch.object(
                AgentService, "update_permissions", new_callable=AsyncMock
            ) as mock_update,
        ):
            mock_get.return_value = mock_agent
            mock_update.return_value = mock_agent

            response = await client.put(
                f"/api/v1/agents/{self.TEST_AGENT_ID}",
                json={"permissions": {"allow": ["payment"]}},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == self.TEST_AGENT_ID
            mock_get.assert_called_once_with(self.TEST_AGENT_ID)
            mock_update.assert_called_once_with(
                self.TEST_AGENT_ID, {"allow": ["payment"]}
            )
