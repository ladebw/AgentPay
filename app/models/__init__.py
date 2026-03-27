from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models so SQLAlchemy can resolve string references
from .agent import Agent  # noqa: E402
from .wallet import Wallet  # noqa: E402
from .invoice import Invoice  # noqa: E402
from .payment import Payment  # noqa: E402
from .webhook import Webhook  # noqa: E402
from .transaction import BlockchainTransaction  # noqa: E402
from .idempotency_key import IdempotencyKey  # noqa: E402

__all__ = [
    "Base",
    "Agent",
    "Wallet",
    "Invoice",
    "Payment",
    "Webhook",
    "BlockchainTransaction",
    "IdempotencyKey",
]
