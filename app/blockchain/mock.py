import hashlib
import time
import uuid
from typing import Any, Dict, Optional

from .base import BlockchainClient, KeyManager


class MockKeyManager(KeyManager):
    """Mock key manager for development."""

    def __init__(self, address: str = "0xMockAddress"):
        self.address = address

    async def get_address(self) -> str:
        return self.address

    async def sign_transaction(self, transaction: Dict[str, Any]) -> str:
        # Return a mock signature
        return f"0x{hashlib.sha256(str(transaction).encode()).hexdigest()}"


class MockBlockchainClient(BlockchainClient):
    """Mock blockchain client for MVP testing."""

    def __init__(self):
        self.balances: Dict[str, float] = {}
        self.transactions: Dict[str, Dict[str, Any]] = {}

    async def get_balance(self, address: str) -> float:
        return self.balances.get(address, 0.0)

    async def transfer_usdc(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        key_manager: Optional[KeyManager] = None,
    ) -> Dict[str, Any]:
        # Simulate balance check
        balance = self.balances.get(from_address, 0.0)
        if balance < amount:
            raise ValueError(f"Insufficient balance: {balance} < {amount}")

        # Update balances
        self.balances[from_address] = balance - amount
        self.balances[to_address] = self.balances.get(to_address, 0.0) + amount

        # Generate mock transaction hash
        tx_hash = f"0x{hashlib.sha256(f'{from_address}{to_address}{amount}{time.time()}'.encode()).hexdigest()[:64]}"

        tx_result = {
            "hash": tx_hash,
            "from": from_address,
            "to": to_address,
            "amount": amount,
            "status": "completed",
            "block_number": 12345678,
            "gas_used": 21000,
            "gas_price_gwei": 50.0,
        }

        self.transactions[tx_hash] = tx_result
        return tx_result

    async def create_wallet(self) -> Dict[str, str]:
        address = f"0x{hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:40]}"
        private_key = f"mock_private_key_{address}"
        return {
            "address": address,
            "private_key": private_key,
        }

    async def get_transaction_receipt(self, tx_hash: str) -> Dict[str, Any]:
        return self.transactions.get(tx_hash, {})

    async def estimate_gas(
        self, from_address: str, to_address: str, amount: float
    ) -> Dict[str, Any]:
        return {
            "gas_limit": 21000,
            "gas_price_gwei": 50.0,
            "total_cost_usd": 0.1,
        }
