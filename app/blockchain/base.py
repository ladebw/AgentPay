from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional


class KeyManagementMode(str, Enum):
    MOCK = "mock"
    KMS = "kms"
    NON_CUSTODIAL = "non_custodial"


class KeyManager(ABC):
    """Abstract key manager for signing transactions."""

    @abstractmethod
    async def get_address(self) -> str:
        """Return the address associated with the managed key."""

    @abstractmethod
    async def sign_transaction(self, transaction: Dict[str, Any]) -> str:
        """Sign a transaction and return the raw signed transaction."""


class BlockchainClient(ABC):
    """Abstract blockchain client for interacting with USDC on Polygon."""

    @abstractmethod
    async def get_balance(self, address: str) -> float:
        """Get USDC balance for address."""

    @abstractmethod
    async def transfer_usdc(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        key_manager: Optional[KeyManager] = None,
    ) -> Dict[str, Any]:
        """
        Transfer USDC between addresses.

        If key_manager is provided, it will be used to sign the transaction.
        Otherwise, the implementation must manage signing internally.
        """

    @abstractmethod
    async def create_wallet(self) -> Dict[str, str]:
        """Generate a new wallet (address, private key)."""

    @abstractmethod
    async def get_transaction_receipt(self, tx_hash: str) -> Dict[str, Any]:
        """Get receipt for a transaction."""

    @abstractmethod
    async def estimate_gas(
        self, from_address: str, to_address: str, amount: float
    ) -> Dict[str, Any]:
        """Estimate gas for a USDC transfer."""
