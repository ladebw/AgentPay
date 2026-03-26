#!/usr/bin/env python3
"""
Test that critical modules can be imported without errors.
"""
import sys
sys.path.insert(0, '.')

try:
    from app.core.config import settings
    from app.core.database import get_db, SessionLocal
    from app.models.agent import Agent
    from app.models.wallet import Wallet
    from app.models.invoice import Invoice
    from app.models.payment import Payment
    from app.models.webhook import Webhook
    from app.models.transaction import BlockchainTransaction
    from app.models.idempotency_key import IdempotencyKey
    from app.blockchain import BlockchainClient, KeyManager, get_blockchain_client
    from app.services.agent import AgentService
    from app.api.middleware.auth import get_current_agent
    print("✅ All imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)