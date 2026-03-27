"""
Tests for payment flow (happy path).
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.payment import (
    PaymentService,
    PaymentAlreadyProcessedError,
    PaymentProcessingError,
)
from app.models.payment import Payment, PaymentStatus


class TestPaymentFlow:
    """Test suite for payment processing."""

    @pytest.fixture
    def mock_db(self):
        """Mock async database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def payment_service(self, mock_db):
        """PaymentService instance with mocked dependencies."""
        service = PaymentService(mock_db)
        service.redis_client = None  # disable Redis for simplicity
        service.blockchain = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_process_payment_success(self, payment_service, mock_db):
        """Happy path: process a payment successfully."""
        # Mock blockchain transfer
        payment_service.blockchain.transfer_usdc.return_value = {"hash": "0xabc123"}

        # Mock database query to return None (no existing payment)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        # Mock internal methods to avoid complex query mocking
        payment_service._get_to_agent_id = AsyncMock(return_value="agent-2")
        with patch.object(
            payment_service, "_send_transaction", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = "0xabc123"

            # Execute
            payment = await payment_service.process_payment(
                agent_id="agent-1", invoice_id="invoice-1", amount=50.0
            )

            # Assertions
            assert payment is not None
            assert payment.transaction_hash == "0xabc123"
            assert payment.status == PaymentStatus.COMPLETED
            assert payment.from_agent_id == "agent-1"
            assert payment.to_agent_id == "agent-2"
            assert payment.amount == 50.0
            # Ensure db commit was called
            mock_db.commit.assert_awaited_once()
            # Ensure no rollback
            mock_db.rollback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_payment_already_processed(self, payment_service, mock_db):
        """Payment with same idempotency key should raise."""
        # Simulate existing payment in database
        mock_existing_payment = Payment(
            id=uuid.uuid4(),
            invoice_id="invoice-1",
            from_agent_id="agent-1",
            status=PaymentStatus.COMPLETED,
        )
        # Mock the database query to return existing payment
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_existing_payment
        mock_db.execute.return_value = result_mock

        # No Redis client
        payment_service.redis_client = None

        with pytest.raises(PaymentAlreadyProcessedError):
            await payment_service.process_payment(
                agent_id="agent-1", invoice_id="invoice-1", amount=50.0
            )

        # Ensure db commit not called
        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_payment_processing_error_rollback(self, payment_service, mock_db):
        """If blockchain transfer fails, rollback should occur."""
        # Mock blockchain transfer to raise exception
        payment_service.blockchain.transfer_usdc.side_effect = Exception(
            "Blockchain error"
        )

        # Mock database query to return None (no existing payment)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        payment_service._get_to_agent_id = AsyncMock(return_value="agent-2")

        with pytest.raises(PaymentProcessingError):
            await payment_service.process_payment(
                agent_id="agent-1", invoice_id="invoice-1", amount=50.0
            )

        # Ensure rollback was called
        mock_db.rollback.assert_awaited_once()
        # Ensure commit not called
        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_send_transaction_success(self, payment_service, mock_db):
        """Test _send_transaction with KMS key manager."""
        # Setup
        payment = Payment(
            id=uuid.uuid4(),
            from_agent_id="agent-1",
            to_agent_id="agent-2",
            amount=100.0,
        )

        # Mock blockchain key manager
        mock_key_manager = AsyncMock()
        mock_key_manager.get_address.return_value = "0xhotwallet"
        payment_service.blockchain.key_manager = mock_key_manager

        # Mock recipient agent query
        mock_recipient = MagicMock()
        mock_recipient.wallet_address = "0xrecipient"
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_recipient
        mock_db.execute.return_value = result_mock

        # Mock blockchain transfer
        payment_service.blockchain.transfer_usdc.return_value = {"hash": "0xtxhash"}

        tx_hash = await payment_service._send_transaction(payment)

        assert tx_hash == "0xtxhash"
        payment_service.blockchain.transfer_usdc.assert_awaited_once_with(
            from_address="0xhotwallet",
            to_address="0xrecipient",
            amount=100.0,
            key_manager=mock_key_manager,
        )
