import logging
import os
from typing import Any, Dict

from eth_account import Account

from app.blockchain.kms_key_manager import KMSKeyManager
from app.core.config import settings
from app.monitoring.sponsorship_metrics import (
    record_sponsored_transaction,
    record_sponsorship_failure,
)
from app.utils.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class GasSponsorshipService:
    """Handle gas sponsorship using OpenZeppelin Defender"""

    def __init__(self, network: str = "polygon"):
        self.network = network
        self.relayer_client = None
        self._init_defender()

    def _init_defender(self):
        """Initialize Defender Relayer client if configured."""
        api_key = os.getenv("DEFENDER_API_KEY")
        api_secret = os.getenv("DEFENDER_API_SECRET")
        relayer_id = os.getenv("DEFENDER_RELAYER_ID")

        if all([api_key, api_secret, relayer_id]):
            try:
                # Conditional import to avoid hard dependency
                from openzeppelin_defender_api import Relayer

                self.relayer_client = Relayer(
                    api_key=api_key, api_secret=api_secret, relayer_id=relayer_id
                )
                logger.info("Defender Relayer client initialized")
            except ImportError:
                logger.warning(
                    "OpenZeppelin Defender SDK not installed. "
                    "Install with 'pip install openzeppelin-defender-api'"
                )
            except Exception as e:
                logger.error(f"Failed to initialize Defender client: {e}")
        else:
            logger.warning(
                "Defender API credentials not set. "
                "Gas sponsorship will not be available."
            )

    def is_enabled(self) -> bool:
        """Return True if sponsorship is configured and enabled."""
        if not settings.enable_gas_sponsorship:
            return False
        return self.relayer_client is not None

    async def send_sponsored_transaction(
        self,
        kms_manager: KMSKeyManager,
        from_address: str,
        to_address: str,
        value: int,
        data: str = "0x",
    ) -> Dict[str, Any]:
        """
        Send transaction with gas sponsorship via Defender Relayer.

        Args:
            kms_manager: KMS key manager instance
            from_address: Sender address (KMS-managed)
            to_address: Recipient address
            value: USDC amount in smallest unit
            data: Transaction data (for USDC transfer)

        Returns:
            Dictionary with transaction hash and receipt details

        Raises:
            ValueError: If Defender client not configured
            RuntimeError: If sponsorship fails
        """
        if not self.relayer_client:
            raise ValueError("Defender Relayer not configured")

        # Circuit breaker to protect against API failures
        circuit_breaker = CircuitBreaker(
            name="defender_relayer", failure_threshold=5, recovery_timeout=60
        )

        with circuit_breaker:
            try:
                # 1. Prepare EIP-712 typed data for meta-transaction
                typed_data = self._build_typed_data(
                    from_address=from_address,
                    to_address=to_address,
                    value=value,
                    data=data,
                )

                # 2. Sign typed data with KMS
                signature = await self._sign_typed_data(kms_manager, typed_data)

                # 3. Submit to Defender Relayer
                tx_hash = await self._submit_to_defender(typed_data, signature)

                # Record success metrics
                # TODO: obtain actual gas cost; for now pass 0.0
                record_sponsored_transaction(
                    chain=self.network, agent_tier="default", gas_cost_usd=0.0
                )

                # 4. Return transaction hash
                return {
                    "transaction_hash": tx_hash,
                    "sponsored": True,
                    "relayer": "defender",
                }
            except Exception as e:
                # Record failure metrics
                record_sponsorship_failure(reason=str(e.__class__.__name__))
                raise

    def _build_typed_data(
        self, from_address: str, to_address: str, value: int, data: str
    ) -> Dict[str, Any]:
        """Construct EIP-712 typed data for meta-transaction."""
        # TODO: Implement proper typed data structure based on Forwarder contract
        # This is a placeholder; actual structure depends on the deployed Forwarder
        typed_data = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                "ForwardRequest": [
                    {"name": "from", "type": "address"},
                    {"name": "to", "type": "address"},
                    {"name": "value", "type": "uint256"},
                    {"name": "gas", "type": "uint256"},
                    {"name": "nonce", "type": "uint256"},
                    {"name": "data", "type": "bytes"},
                ],
            },
            "primaryType": "ForwardRequest",
            "domain": {
                "name": "GaslessForwarder",
                "version": "1",
                "chainId": 137,  # Polygon mainnet
                "verifyingContract": "0x...",  # Should be from config
            },
            "message": {
                "from": from_address,
                "to": to_address,
                "value": value,
                "gas": 100000,  # Estimate
                "nonce": 0,  # Need to fetch from forwarder contract
                "data": data,
            },
        }
        return typed_data

    async def _sign_typed_data(
        self, kms_manager: KMSKeyManager, typed_data: Dict[str, Any]
    ) -> str:
        """Sign EIP-712 typed data using KMS."""
        # Convert typed data to signable hash
        account = Account()
        signable_hash = account._hash_eip712_message(typed_data)
        # Sign hash using KMS key manager
        r, s, recovery_id = await kms_manager.sign_hash(signable_hash)
        # Encode signature as 65-byte hex string (r, s, v) where v = recovery_id + 27
        v = recovery_id + 27
        signature = (
            r.to_bytes(32, "big") + s.to_bytes(32, "big") + v.to_bytes(1, "big")
        ).hex()
        return signature

    async def _submit_to_defender(
        self, typed_data: Dict[str, Any], signature: str
    ) -> str:
        """Submit signed meta-transaction to Defender Relayer."""
        if not self.relayer_client:
            raise ValueError("Defender Relayer not configured")
        try:
            # Construct a transaction from typed data and signature
            # For now, we'll just call send_transaction with placeholder
            # This will fail if the SDK is not properly configured, but we catch.
            tx = await self.relayer_client.send_transaction(
                {
                    "to": typed_data["message"]["to"],
                    "data": typed_data["message"]["data"],
                    "value": typed_data["message"]["value"],
                    "gas": typed_data["message"]["gas"],
                }
            )
            return tx.hash
        except Exception as e:
            logger.error(f"Defender submission failed: {e}")
            raise RuntimeError(f"Defender submission failed: {e}")

    async def get_sponsorship_status(self, agent_id: str) -> Dict[str, Any]:
        """Check if an agent is eligible for sponsorship and their limits."""
        # TODO: Implement based on agent tier, spending caps, etc.
        return {
            "eligible": True,
            "daily_limit_usd": settings.max_sponsor_amount_usd,
            "remaining_today_usd": settings.max_sponsor_amount_usd,
            "whitelisted": agent_id in settings.sponsor_whitelist,
        }
