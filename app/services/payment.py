import asyncio
import uuid

from redis import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.blockchain import get_blockchain_client
from app.core.config import settings
from app.models.agent import Agent
from app.models.invoice import Invoice
from app.models.payment import Payment, PaymentStatus


class PaymentService:
    """Service for processing payments with idempotency."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.blockchain = get_blockchain_client()
        self.redis_client = None
        if settings.redis_url:
            self.redis_client = Redis.from_url(settings.redis_url)

    async def process_payment(
        self, agent_id: str, invoice_id: str, amount: float
    ) -> Payment:
        """Idempotent payment processing."""
        idempotency_key = f"payment:{agent_id}:{invoice_id}"

        # Check if already processed
        if self.redis_client:
            if await asyncio.to_thread(self.redis_client.get, idempotency_key):
                raise PaymentAlreadyProcessedError()

        # Acquire lock to prevent concurrent processing
        lock_key = f"lock:{idempotency_key}"
        lock = None
        if self.redis_client:
            lock = await asyncio.to_thread(self.redis_client.lock, lock_key, timeout=30)
            acquired = await asyncio.to_thread(lock.acquire, blocking=True)
            if not acquired:
                raise PaymentProcessingLockError()

        try:
            # Check again in database (in case Redis expired)
            stmt = select(Payment).where(
                Payment.invoice_id == invoice_id,
                Payment.from_agent_id == agent_id,
                Payment.status.in_([PaymentStatus.COMPLETED, PaymentStatus.PROCESSING]),
            )
            result = await self.db.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                raise PaymentAlreadyProcessedError()

            # Create payment record
            payment = Payment(
                id=uuid.uuid4(),
                invoice_id=invoice_id,
                from_agent_id=agent_id,
                to_agent_id=await self._get_to_agent_id(invoice_id),
                amount=amount,
                status=PaymentStatus.PROCESSING,
                idempotency_key=idempotency_key,
            )
            self.db.add(payment)
            await self.db.flush()

            # Process payment on blockchain
            transaction_hash = await self._send_transaction(payment)
            payment.transaction_hash = transaction_hash
            payment.status = PaymentStatus.COMPLETED

            await self.db.commit()

            # Store idempotency key in Redis with TTL
            if self.redis_client:
                await asyncio.to_thread(
                    self.redis_client.setex,
                    idempotency_key,
                    settings.idempotency_key_ttl,
                    "processed",
                )

            return payment
        except Exception as e:
            await self.db.rollback()
            raise PaymentProcessingError(f"Payment processing failed: {str(e)}")
        finally:
            if lock:
                await asyncio.to_thread(lock.release)

    async def _get_to_agent_id(self, invoice_id: str) -> str:
        """Retrieve the recipient agent ID from the invoice."""
        stmt = select(Invoice).where(Invoice.id == invoice_id)
        result = await self.db.execute(stmt)
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        return invoice.to_agent_id

    async def _send_transaction(self, payment: Payment) -> str:
        """Send transaction to blockchain."""
        # Get recipient agent's wallet address
        stmt = select(Agent).where(Agent.id == payment.to_agent_id)
        result = await self.db.execute(stmt)
        to_agent = result.scalar_one_or_none()
        if not to_agent:
            raise ValueError(f"Recipient agent {payment.to_agent_id} not found")
        to_address = to_agent.wallet_address

        # Determine sender address (system's hot wallet)
        # If blockchain client has a key manager, use its address
        if hasattr(self.blockchain, "key_manager") and self.blockchain.key_manager:
            from_address = await self.blockchain.key_manager.get_address()
        elif hasattr(self.blockchain, "private_key") and self.blockchain.private_key:
            # Derive address from private key (for non-custodial mode)
            from eth_account import Account

            from_address = Account.from_key(self.blockchain.private_key).address
        else:
            # Fallback to payer's wallet address (may not be signable)
            stmt = select(Agent).where(Agent.id == payment.from_agent_id)
            result = await self.db.execute(stmt)
            from_agent = result.scalar_one_or_none()
            if not from_agent:
                raise ValueError(f"Sender agent {payment.from_agent_id} not found")
            from_address = from_agent.wallet_address

        # Perform USDC transfer
        tx_result = await self.blockchain.transfer_usdc(
            from_address=from_address,
            to_address=to_address,
            amount=float(payment.amount),
            key_manager=(
                self.blockchain.key_manager
                if hasattr(self.blockchain, "key_manager")
                and self.blockchain.key_manager
                else None
            ),
        )

        return tx_result["hash"]


class PaymentAlreadyProcessedError(Exception):
    """Raised when a payment with the same idempotency key has already been processed."""


class PaymentProcessingLockError(Exception):
    """Raised when unable to acquire lock for payment processing."""


class PaymentProcessingError(Exception):
    """Generic payment processing error."""
