#!/usr/bin/env python3
"""
AGENTPAY Demo: On-Chain Payments for AI Agents

This script demonstrates the core payment flow using the mock blockchain client.
Run with the server already started (uvicorn main:app --reload).
"""

import asyncio
import aiohttp
import sys


async def main():
    base_url = "http://localhost:8000/api/v1"
    
    async with aiohttp.ClientSession() as session:
        print("=== AGENTPAY DEMO: On-Chain Payments ===\n")
        
        # 1. Create two agents
        print("1. Creating agents...")
        async with session.post(f"{base_url}/agents", json={"name": "Agent A"}) as resp:
            agent_a = await resp.json()
        async with session.post(f"{base_url}/agents", json={"name": "Agent B"}) as resp:
            agent_b = await resp.json()
        
        print(f"   Agent A created: {agent_a['id']}")
        print(f"   Agent B created: {agent_b['id']}")
        api_key_a = agent_a['api_key']
        
        # 2. Fund Agent A (mock funding)
        print("\n2. Funding Agent A with 1000 USDC...")
        async with session.post(
            f"{base_url}/wallets/fund",
            json={"amount": 1000},
            headers={"X-API-Key": api_key_a}
        ) as resp:
            fund_result = await resp.json()
        print(f"   {fund_result.get('message')}")
        
        # 3. Agent B creates invoice (requires API key of Agent B, but we'll use admin)
        print("\n3. Agent B creates invoice for 150 USDC...")
        async with session.post(
            f"{base_url}/invoices",
            json={
                "to_agent_id": agent_a['id'],
                "amount": 150,
                "currency": "USDC"
            },
            headers={"X-API-Key": agent_b.get('api_key', '')}
        ) as resp:
            invoice = await resp.json()
        print(f"   Invoice created: {invoice['id']}")
        
        # 4. Agent A pays invoice
        print("\n4. Agent A pays invoice with on-chain USDC transfer...")
        async with session.post(
            f"{base_url}/payments",
            json={"invoice_id": invoice['id']},
            headers={"X-API-Key": api_key_a}
        ) as resp:
            payment = await resp.json()
        print(f"   Payment completed!")
        print(f"   Transaction hash: {payment.get('transaction_hash')}")
        
        # 5. Check final balances
        print("\n5. Final on-chain balances:")
        async with session.get(
            f"{base_url}/wallets/{agent_a['id']}",
            headers={"X-API-Key": api_key_a}
        ) as resp:
            balance_a = await resp.json()
        async with session.get(
            f"{base_url}/wallets/{agent_b['id']}",
            headers={"X-API-Key": agent_b.get('api_key', '')}
        ) as resp:
            balance_b = await resp.json()
        
        print(f"   Agent A balance: {balance_a.get('balance')} USDC")
        print(f"   Agent B balance: {balance_b.get('balance')} USDC")
        
        print("\n=== Demo completed successfully! ===")


if __name__ == "__main__":
    asyncio.run(main())