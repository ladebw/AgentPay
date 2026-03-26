import asyncio
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_der_public_key
from eth_account import Account
from eth_account._utils.legacy_transactions import (
    encode_transaction,
    serializable_unsigned_transaction_from_dict,
)
from eth_account._utils.signing import to_eth_v
from eth_account.typed_transactions import TypedTransaction
from eth_keys import KeyAPI

from .base import KeyManager


class KMSKeyManager(KeyManager):
    """Key manager using AWS KMS for signing."""

    class KMSKeyManagerError(Exception):
        """Base exception for KMS key manager errors."""

    def __init__(self, key_id: str, region: str = "us-east-1"):
        self.key_id = key_id
        self.region = region
        self.client = boto3.client("kms", region_name=region)
        # Cache the public key address
        self._address = None
        # Cache the public key bytes
        self._public_key_bytes = None

    def validate_kms_key(self):
        """Validate KMS key has correct permissions and type"""
        try:
            response = self.client.describe_key(KeyId=self.key_id)

            # Check key type
            key_spec = response["KeyMetadata"]["KeySpec"]
            if key_spec != "ECC_SECG_P256K1":
                raise self.KMSKeyManagerError(
                    f"KMS key must be ECC_SECG_P256K1, got {key_spec}"
                )

            # Check key state
            key_state = response["KeyMetadata"]["KeyState"]
            if key_state != "Enabled":
                raise self.KMSKeyManagerError(
                    f"KMS key must be Enabled, got {key_state}"
                )

            # Check key usage includes SIGN_VERIFY
            key_usage = response["KeyMetadata"]["KeyUsage"]
            if key_usage != "SIGN_VERIFY":
                raise self.KMSKeyManagerError(
                    f"KMS key must have SIGN_VERIFY usage, got {key_usage}"
                )

        except Exception as e:
            raise self.KMSKeyManagerError(f"KMS key validation failed: {str(e)}")

    async def get_address(self) -> str:
        """Return the Ethereum address derived from the KMS key's public key."""
        if self._address is None:
            # Validate KMS key before using it
            self.validate_kms_key()
            try:
                # Retrieve public key from KMS
                response = await asyncio.to_thread(
                    self.client.get_public_key, KeyId=self.key_id
                )
            except ClientError as e:
                raise self.KMSKeyManagerError(f"Failed to get public key from KMS: {e}")
            public_key_der = response["PublicKey"]

            # Parse DER-encoded public key (X.509 SubjectPublicKeyInfo)
            try:
                pub_key = load_der_public_key(public_key_der)
            except Exception as e:
                raise self.KMSKeyManagerError(f"Failed to parse public key: {e}")

            # Extract uncompressed SEC1 representation (0x04 + X + Y)
            try:
                uncompressed = pub_key.public_bytes(
                    encoding=serialization.Encoding.X962,
                    format=serialization.PublicFormat.UncompressedPoint,
                )
            except Exception as e:
                raise self.KMSKeyManagerError(
                    f"Failed to extract uncompressed public key: {e}"
                )
            # uncompressed is 65 bytes: 0x04 + 32-byte X + 32-byte Y
            # Compute Ethereum address using eth_keys
            try:
                # eth_keys expects raw 64-byte X+Y concatenated
                raw_key = uncompressed[1:]  # strip leading 0x04
                public_key = KeyAPI.PublicKey(raw_key)
                self._address = public_key.to_checksum_address()
            except Exception as e:
                raise self.KMSKeyManagerError(f"Failed to derive Ethereum address: {e}")
        return self._address

    async def sign_transaction(self, transaction: Dict[str, Any]) -> str:
        """Sign a transaction using AWS KMS."""
        # Ensure chainId is present
        if "chainId" not in transaction:
            transaction["chainId"] = 137  # Polygon mainnet

        # Validate KMS key before signing
        self.validate_kms_key()

        # Convert transaction dict to unsigned transaction object
        unsigned_transaction = serializable_unsigned_transaction_from_dict(
            transaction, blobs=None
        )
        hash_to_sign = unsigned_transaction.hash()

        # Call KMS sign API
        response = await asyncio.to_thread(
            self.client.sign,
            KeyId=self.key_id,
            Message=hash_to_sign,
            SigningAlgorithm="ECDSA_SHA_256",
            MessageType="DIGEST",
        )
        der_signature = response["Signature"]

        # Parse DER signature to r, s integers
        r, s = self._parse_der_signature(der_signature)

        # Determine recovery parameter v by trying both possibilities
        my_address = await self.get_address()

        recovery_id = None
        for candidate in (0, 1):
            if isinstance(unsigned_transaction, TypedTransaction):
                # For typed transactions, v is just candidate (0 or 1)
                v = candidate
            else:
                # For legacy transactions, apply EIP-155 chain ID adjustment
                chain_id = transaction.get("chainId", 0)
                v = to_eth_v(candidate, chain_id if chain_id else None)

            # Build signed transaction with candidate v
            signed_tx = encode_transaction(unsigned_transaction, vrs=(v, r, s))
            try:
                recovered = Account.recover_transaction(signed_tx)
            except Exception:
                continue
            if recovered.lower() == my_address.lower():
                recovery_id = candidate
                break

        if recovery_id is None:
            raise ValueError("Could not determine recovery ID")

        # Compute final v
        if isinstance(unsigned_transaction, TypedTransaction):
            v = recovery_id
        else:
            chain_id = transaction.get("chainId", 0)
            v = to_eth_v(recovery_id, chain_id if chain_id else None)

        # Build final signed transaction
        signed_tx = encode_transaction(unsigned_transaction, vrs=(v, r, s))
        return signed_tx.hex()

    async def sign_hash(self, message_hash: bytes) -> tuple[int, int, int]:
        """Sign a message hash using AWS KMS and return (r, s, recovery_id)."""
        self.validate_kms_key()
        response = await asyncio.to_thread(
            self.client.sign,
            KeyId=self.key_id,
            Message=message_hash,
            SigningAlgorithm="ECDSA_SHA_256",
            MessageType="DIGEST",
        )
        der_signature = response["Signature"]
        r, s = self._parse_der_signature(der_signature)
        my_address = await self.get_address()
        recovery_id = None
        for candidate in (0, 1):
            # For message signing, v = candidate + 27
            v = candidate + 27
            # Recover address from signature
            from eth_account import Account

            signature_bytes = (
                r.to_bytes(32, "big") + s.to_bytes(32, "big") + v.to_bytes(1, "big")
            )
            recovered = Account._recover_hash(message_hash, signature_bytes)
            if recovered.lower() == my_address.lower():
                recovery_id = candidate
                break
        if recovery_id is None:
            raise ValueError("Could not determine recovery ID")
        return r, s, recovery_id

    def _compute_v(self, chain_id: int, recovery_id: int) -> int:
        """Compute v parameter according to EIP-155."""
        if chain_id:
            return chain_id * 2 + 35 + recovery_id
        else:
            return 27 + recovery_id

    async def _get_public_key_bytes(self) -> bytes:
        """Return the uncompressed public key bytes (cached)."""
        if self._public_key_bytes is None:
            response = await asyncio.to_thread(
                self.client.get_public_key, KeyId=self.key_id
            )
            public_key_der = response["PublicKey"]
            pub_key = load_der_public_key(public_key_der)
            uncompressed = pub_key.public_bytes(
                encoding=serialization.Encoding.X962,
                format=serialization.PublicFormat.UncompressedPoint,
            )
            self._public_key_bytes = uncompressed
        return self._public_key_bytes

    def _parse_der_signature(self, der_signature: bytes) -> tuple[int, int]:
        """Parse DER-encoded ECDSA signature into (r, s) integers."""
        # Simplified DER parser for ECDSA signature
        # Format: 0x30 [len] 0x02 [len_r] [r] 0x02 [len_s] [s]
        if der_signature[0] != 0x30:
            raise ValueError("Invalid DER signature: missing SEQUENCE")
        pos = 1
        # decode length (could be multi-byte but assume single byte < 128)
        seq_len = der_signature[pos]
        pos += 1
        if seq_len > 127:
            # length encoded with multiple bytes, skip for now
            raise ValueError("Multi-byte length not supported")
        # expect 0x02
        if der_signature[pos] != 0x02:
            raise ValueError("Invalid DER signature: missing INTEGER tag for r")
        pos += 1
        r_len = der_signature[pos]
        pos += 1
        r_bytes = der_signature[pos : pos + r_len]
        pos += r_len
        # expect 0x02
        if der_signature[pos] != 0x02:
            raise ValueError("Invalid DER signature: missing INTEGER tag for s")
        pos += 1
        s_len = der_signature[pos]
        pos += 1
        s_bytes = der_signature[pos : pos + s_len]
        # Convert bytes to integer (big-endian)
        r = int.from_bytes(r_bytes, "big")
        s = int.from_bytes(s_bytes, "big")
        return r, s
