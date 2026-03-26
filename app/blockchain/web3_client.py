import json
import os
from typing import Any, Dict, Optional

from eth_account import Account
from web3 import Web3

from .base import BlockchainClient, KeyManager


class Web3KeyManager(KeyManager):
    """Key manager using Web3 and a private key (for development only)."""

    def __init__(self, private_key: str):
        self.account = Account.from_key(private_key)

    async def get_address(self) -> str:
        return self.account.address

    async def sign_transaction(self, transaction: Dict[str, Any]) -> str:
        signed = self.account.sign_transaction(transaction)
        return signed.rawTransaction.hex()


class Web3BlockchainClient(BlockchainClient):
    """Real blockchain client using Web3.py."""

    def __init__(
        self,
        rpc_url: str,
        usdc_address: str,
        private_key: Optional[str] = None,
        key_manager: Optional[KeyManager] = None,
    ):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.usdc_address = usdc_address
        self.private_key = private_key
        self.key_manager = key_manager

        # Load USDC ABI
        abi_path = os.path.join(os.path.dirname(__file__), "usdc_abi.json")
        with open(abi_path, "r") as f:
            usdc_abi = json.load(f)
        self.usdc_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(usdc_address), abi=usdc_abi
        )

    async def get_balance(self, address: str) -> float:
        balance = self.usdc_contract.functions.balanceOf(
            self.w3.to_checksum_address(address)
        ).call()
        decimals = self.usdc_contract.functions.decimals().call()
        return balance / (10**decimals)

    async def transfer_usdc(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        key_manager: Optional[KeyManager] = None,
    ) -> Dict[str, Any]:
        # Convert amount to USDC decimals (6)
        decimals = self.usdc_contract.functions.decimals().call()
        amount_wei = int(amount * (10**decimals))

        # Build transaction
        nonce = self.w3.eth.get_transaction_count(from_address)
        tx = self.usdc_contract.functions.transfer(
            self.w3.to_checksum_address(to_address), amount_wei
        ).build_transaction(
            {
                "chainId": self.w3.eth.chain_id,
                "gas": 200000,
                "gasPrice": self.w3.eth.gas_price,
                "nonce": nonce,
                "from": from_address,
            }
        )

        # Sign transaction
        signing_key_manager = (
            key_manager if key_manager is not None else self.key_manager
        )
        if signing_key_manager:
            signed_tx_hex = await signing_key_manager.sign_transaction(tx)
            signed_tx = self.w3.eth.send_raw_transaction(signed_tx_hex)
        elif self.private_key:
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            signed_tx = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        else:
            raise ValueError("No signing method provided")

        # Wait for receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(signed_tx)

        return {
            "hash": receipt.transactionHash.hex(),
            "block_number": receipt.blockNumber,
            "gas_used": receipt.gasUsed,
            "status": "completed" if receipt.status == 1 else "failed",
        }

    async def create_wallet(self) -> Dict[str, str]:
        account = self.w3.eth.account.create()
        return {
            "address": account.address,
            "private_key": account.key.hex(),
        }

    async def get_transaction_receipt(self, tx_hash: str) -> Dict[str, Any]:
        receipt = self.w3.eth.get_transaction_receipt(tx_hash)
        return dict(receipt) if receipt else {}

    async def estimate_gas(
        self, from_address: str, to_address: str, amount: float
    ) -> Dict[str, Any]:
        decimals = self.usdc_contract.functions.decimals().call()
        amount_wei = int(amount * (10**decimals))
        gas = self.usdc_contract.functions.transfer(
            self.w3.to_checksum_address(to_address), amount_wei
        ).estimate_gas({"from": from_address})
        gas_price = self.w3.eth.gas_price
        return {
            "gas_limit": gas,
            "gas_price_gwei": self.w3.from_wei(gas_price, "gwei"),
            "total_cost_usd": float(gas * gas_price)
            / 1e18
            * 3000,  # approximate USD using ETH price
        }
