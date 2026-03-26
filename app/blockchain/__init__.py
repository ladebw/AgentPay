from .base import BlockchainClient, KeyManager, KeyManagementMode
from .mock import MockBlockchainClient, MockKeyManager
from .web3_client import Web3BlockchainClient, Web3KeyManager
from .kms_key_manager import KMSKeyManager
from app.core.config import settings


def get_blockchain_client() -> BlockchainClient:
    """Factory function to get appropriate blockchain client based on settings."""
    if settings.key_management_mode == KeyManagementMode.MOCK:
        return MockBlockchainClient()
    
    # Real blockchain client (Polygon)
    client = Web3BlockchainClient(
        rpc_url=settings.rpc_url,
        usdc_address=settings.usdc_address,
        private_key=settings.private_key if settings.key_management_mode == KeyManagementMode.NON_CUSTODIAL else None
    )
    
    if settings.key_management_mode == KeyManagementMode.KMS:
        if not settings.kms_key_id:
            raise ValueError("KMS key ID must be set when using KMS mode")
        key_manager = KMSKeyManager(
            key_id=settings.kms_key_id,
            region=settings.kms_region or "us-east-1"
        )
        client.key_manager = key_manager
    # For NON_CUSTODIAL mode, private_key is already set in client
    
    return client


__all__ = [
    "BlockchainClient",
    "KeyManager",
    "KeyManagementMode",
    "MockBlockchainClient",
    "MockKeyManager",
    "Web3BlockchainClient",
    "Web3KeyManager",
    "get_blockchain_client",
]