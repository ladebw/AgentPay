"""
Unit tests for KMSKeyManager.
"""
import asyncio
import pytest
from unittest.mock import MagicMock, patch
from app.blockchain.kms_key_manager import KMSKeyManager


class TestKMSKeyManager:
    """Test suite for KMSKeyManager."""
    
    @pytest.fixture
    def mock_kms_client(self):
        """Mock AWS KMS client."""
        with patch('boto3.client') as mock_client:
            # Configure default describe_key response for validation
            mock_client.return_value.describe_key.return_value = {
                'KeyMetadata': {
                    'KeySpec': 'ECC_SECG_P256K1',
                    'KeyState': 'Enabled',
                    'KeyUsage': 'SIGN_VERIFY'
                }
            }
            yield mock_client
    
    @pytest.fixture
    def kms_key_manager(self, mock_kms_client):
        """Create a KMSKeyManager instance with mocked client."""
        manager = KMSKeyManager(key_id='alias/test-key')
        manager.client = mock_kms_client.return_value
        return manager
    
    @pytest.mark.asyncio
    async def test_get_address_success(self, kms_key_manager, mock_kms_client):
        """Test successful address derivation."""
        # Mock KMS get_public_key response with a known public key
        # This public key corresponds to a known Ethereum address
        # For simplicity, we'll use a dummy DER-encoded public key
        # The actual derivation will be tested with integration tests.
        mock_response = {
            'PublicKey': b'fake-der-public-key'
        }
        kms_key_manager.client.get_public_key.return_value = mock_response
        
        # Mock the cryptography and eth_keys parsing to return a known address
        with patch('app.blockchain.kms_key_manager.load_der_public_key') as mock_load, \
             patch('app.blockchain.kms_key_manager.serialization') as mock_serial, \
             patch('eth_keys.KeyAPI.PublicKey') as mock_pubkey_cls:
            mock_pub_key = MagicMock()
            mock_load.return_value = mock_pub_key
            # uncompressed representation with leading 0x04
            uncompressed = b'\x04' + b'x' * 64
            mock_pub_key.public_bytes.return_value = uncompressed
            mock_eth_pubkey = MagicMock()
            mock_eth_pubkey.to_checksum_address.return_value = '0x1234567890123456789012345678901234567890'
            mock_pubkey_cls.return_value = mock_eth_pubkey
            
            address = await kms_key_manager.get_address()
            
            assert address == '0x1234567890123456789012345678901234567890'
            kms_key_manager.client.get_public_key.assert_called_once_with(KeyId='alias/test-key')
            # Ensure the constructor was called with raw 64-byte key (strip leading 0x04)
            mock_pubkey_cls.assert_called_once_with(b'x' * 64)
    
    @pytest.mark.asyncio
    async def test_get_address_cached(self, kms_key_manager):
        """Test that address is cached after first call."""
        kms_key_manager._address = '0xcached'
        address = await kms_key_manager.get_address()
        assert address == '0xcached'
        # Ensure no KMS call was made
        kms_key_manager.client.get_public_key.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_sign_transaction_success(self, kms_key_manager, mock_kms_client):
        """Test successful transaction signing."""
        # Mock KMS sign response with a DER signature
        mock_response = {
            'Signature': b'0x30fakeDER'
        }
        kms_key_manager.client.sign.return_value = mock_response
        
        # Mock DER parsing to return known r, s
        with patch.object(kms_key_manager, '_parse_der_signature') as mock_parse:
            mock_parse.return_value = (12345, 67890)
            # Mock address recovery
            with patch.object(kms_key_manager, 'get_address') as mock_get_addr:
                mock_get_addr.return_value = '0x1234567890123456789012345678901234567890'
                # Mock transaction serialization and encoding
                with patch('app.blockchain.kms_key_manager.serializable_unsigned_transaction_from_dict') as mock_serializable, \
                     patch('app.blockchain.kms_key_manager.encode_transaction') as mock_encode, \
                     patch('eth_account.Account.recover_transaction') as mock_recover:
                    mock_unsigned = MagicMock()
                    mock_unsigned.hash.return_value = b'hash'
                    mock_serializable.return_value = mock_unsigned
                    mock_encode.return_value = b'signed_raw_tx'
                    mock_recover.return_value = '0x1234567890123456789012345678901234567890'
                    
                    transaction = {
                        'chainId': 137,
                        'nonce': 1,
                        'gas': 21000,
                        'gasPrice': 1000000000,
                        'to': '0x1111111111111111111111111111111111111111',
                        'value': 0,
                        'data': b''
                    }
                    signed = await kms_key_manager.sign_transaction(transaction)
                    
                    assert signed == '7369676e65645f7261775f7478'  # hex of b'signed_raw_tx'
                    kms_key_manager.client.sign.assert_called_once_with(
                        KeyId='alias/test-key',
                        Message=b'hash',
                        SigningAlgorithm='ECDSA_SHA_256',
                        MessageType='DIGEST'
                    )
    
    @pytest.mark.asyncio
    async def test_sign_transaction_chain_id_default(self, kms_key_manager):
        """Test that missing chainId defaults to Polygon mainnet."""
        # Mock KMS sign to avoid actual call
        kms_key_manager.client.sign.return_value = {'Signature': b'0x30fakeDER'}
        # Mock DER parsing
        with patch.object(kms_key_manager, '_parse_der_signature') as mock_parse:
            mock_parse.return_value = (12345, 67890)
            # Mock address recovery
            with patch.object(kms_key_manager, 'get_address') as mock_get_addr:
                mock_get_addr.return_value = '0x1234567890123456789012345678901234567890'
                # Mock transaction serialization and encoding
                with patch('app.blockchain.kms_key_manager.serializable_unsigned_transaction_from_dict') as mock_serializable, \
                     patch('app.blockchain.kms_key_manager.encode_transaction') as mock_encode, \
                     patch('eth_account.Account.recover_transaction') as mock_recover:
                    mock_unsigned = MagicMock()
                    mock_unsigned.hash.return_value = b'hash'
                    mock_serializable.return_value = mock_unsigned
                    mock_encode.return_value = b'signed'
                    mock_recover.return_value = '0x1234567890123456789012345678901234567890'
                    
                    transaction = {
                        'nonce': 1,
                        'gas': 21000,
                        'gasPrice': 1000000000,
                        'to': '0x1111111111111111111111111111111111111111',
                        'value': 0,
                        'data': b''
                    }
                    # Call sign_transaction
                    await kms_key_manager.sign_transaction(transaction)
                    
                    # Verify that chainId was added to the transaction dict
                    # The mock_serializable was called with a dict containing chainId
                    call_args = mock_serializable.call_args
                    assert call_args is not None
                    # The first argument is the transaction dict
                    tx_dict = call_args[0][0]
                    assert tx_dict['chainId'] == 137
    
    @pytest.mark.asyncio
    async def test_sign_eip1559_transaction(self, kms_key_manager, mock_kms_client):
        """Test signing EIP-1559 transaction."""
        # Mock KMS sign response with a DER signature
        mock_response = {
            'Signature': b'0x30fakeDER'
        }
        kms_key_manager.client.sign.return_value = mock_response
        
        # Mock DER parsing to return known r, s
        with patch.object(kms_key_manager, '_parse_der_signature') as mock_parse:
            mock_parse.return_value = (12345, 67890)
            # Mock address recovery
            with patch.object(kms_key_manager, 'get_address') as mock_get_addr:
                mock_get_addr.return_value = '0x1234567890123456789012345678901234567890'
                # Mock transaction serialization and encoding
                with patch('app.blockchain.kms_key_manager.serializable_unsigned_transaction_from_dict') as mock_serializable, \
                     patch('app.blockchain.kms_key_manager.encode_transaction') as mock_encode, \
                     patch('eth_account.Account.recover_transaction') as mock_recover:
                    mock_unsigned = MagicMock()
                    # Simulate TypedTransaction
                    mock_unsigned.hash.return_value = b'hash'
                    mock_serializable.return_value = mock_unsigned
                    mock_encode.return_value = b'signed_raw_tx'
                    mock_recover.return_value = '0x1234567890123456789012345678901234567890'
                    
                    transaction = {
                        'type': 2,
                        'chainId': 137,
                        'nonce': 1,
                        'maxPriorityFeePerGas': 2000000000,
                        'maxFeePerGas': 3000000000,
                        'gas': 21000,
                        'to': '0x1111111111111111111111111111111111111111',
                        'value': 1000000000000000000,
                        'data': b'',
                    }
                    signed = await kms_key_manager.sign_transaction(transaction)
                    
                    assert signed == '7369676e65645f7261775f7478'  # hex of b'signed_raw_tx'
                    kms_key_manager.client.sign.assert_called_once_with(
                        KeyId='alias/test-key',
                        Message=b'hash',
                        SigningAlgorithm='ECDSA_SHA_256',
                        MessageType='DIGEST'
                    )

    @pytest.mark.asyncio
    async def test_kms_key_disabled(self, kms_key_manager, mock_kms_client):
        """Test error when KMS key is disabled."""
        # Mock describe_key to return disabled key
        mock_kms_client.describe_key.return_value = {
            'KeyMetadata': {
                'KeyState': 'Disabled',
                'KeySpec': 'ECC_SECG_P256K1',
                'KeyUsage': 'SIGN_VERIFY'
            }
        }
        with pytest.raises(kms_key_manager.KMSKeyManagerError):
            await kms_key_manager.get_address()

    def test_parse_der_signature_valid(self, kms_key_manager):
        """Test DER signature parsing."""
        # Example DER signature (shortened)
        der = bytes.fromhex('304402200000000000000000000000000000000000000000000000000000000000000123022000000000000000000000000000000000000000000000000000000000000045')
        r, s = kms_key_manager._parse_der_signature(der)
        assert r == 0x123
        assert s == 0x45
    
    def test_compute_v_with_chain_id(self, kms_key_manager):
        """Test v computation with chainId."""
        assert kms_key_manager._compute_v(137, 0) == 137 * 2 + 35 + 0
        assert kms_key_manager._compute_v(137, 1) == 137 * 2 + 35 + 1
    
    def test_compute_v_without_chain_id(self, kms_key_manager):
        """Test v computation without chainId (legacy)."""
        assert kms_key_manager._compute_v(0, 0) == 27
        assert kms_key_manager._compute_v(0, 1) == 28


if __name__ == '__main__':
    pytest.main([__file__, '-v'])