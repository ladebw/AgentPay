from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

Base = declarative_base()

# Import all models here to ensure they are registered with Base
from .agent import Agent
from .wallet import Wallet
from .invoice import Invoice
from .payment import Payment
from .webhook import Webhook
from .transaction import BlockchainTransaction
from .idempotency_key import IdempotencyKey

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