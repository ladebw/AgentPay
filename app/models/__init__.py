from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Import all models here to ensure they are registered with Base
from .agent import Agent
from .idempotency_key import IdempotencyKey
from .invoice import Invoice
from .payment import Payment
from .transaction import BlockchainTransaction
from .wallet import Wallet
from .webhook import Webhook

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
