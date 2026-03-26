<h1 align="center">AGENTPAY</h1>
<p align="center">
  On-Chain Identity + Payment Infrastructure for AI Agents
</p>
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green" />
</p>

<p align="center">
  Production-ready MVP for AI agent payments using direct on-chain USDC transfers (no escrow). 
  Built with FastAPI, SQLAlchemy, and a pluggable blockchain layer.
</p>



## Features

- **Agent Identity**: API-key based authentication with hashed keys.
- **On-Chain Wallets**: Polygon USDC wallets, balances queried directly from blockchain.
- **Invoice System**: Request payments between agents with status tracking.
- **Direct On-Chain Payments**: Atomic USDC transfers (no escrow).
- **Webhook System**: Event-driven notifications with retry logic.
- **Blockchain Abstraction**: Mock client for MVP, ready for Web3.py integration.
- **Key Management**: Secure key management with KMS, mock, and non‑custodial modes.
- **Idempotent Payments**: Prevent duplicate payments via idempotency keys.
- **Atomic Transactions**: Two‑phase commit between database and blockchain.
- **API Security**: Rate limiting, CORS, and permission‑based access control.

## Architecture

```
agentpay/
├── app/
│   ├── api/                 # FastAPI routers
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response models
│   ├── services/            # Business logic
│   ├── blockchain/          # Abstract client + mock/Web3 implementations
│   └── core/                # Config, database, security
├── agentpay_sdk/            # Python SDK for external integration
├── migrations/              # Alembic database migrations
├── scripts/                 # Database init, etc.
├── tests/                   # Pytest test suite
└── demo.py                  # End‑to‑end demonstration
```

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/ladebw/AgentPay.git
cd agentpay
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings (database, blockchain, etc.)
```

### 2. Database

```bash
python scripts/init_db.py
alembic upgrade head
```

### 3. Run Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test with cURL

Create an agent:

```bash
curl -X POST "http://localhost:8000/api/v1/agents" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Agent"}'
```

Create an invoice:

```bash
curl -X POST "http://localhost:8000/api/v1/invoices" \
  -H "X-API-Key: <your_api_key>" \
  -H "Content-Type: application/json" \
  -d '{"to_agent_id": "<recipient_id>", "amount": 100, "currency": "USDC"}'
```

Pay invoice:

```bash
curl -X POST "http://localhost:8000/api/v1/payments" \
  -H "X-API-Key: <your_api_key>" \
  -H "Content-Type: application/json" \
  -d '{"invoice_id": "<invoice_id>"}'
```

## Production Deployment

### Blockchain Integration

Replace the mock client with a real Web3 client:

1. Set `KEY_MANAGEMENT_MODE=kms` or `non_custodial` in `.env`.
2. Provide `RPC_URL`, `USDC_ADDRESS`, and `PRIVATE_KEY` (or KMS key ID).
3. Deploy with a secure key‑management solution (HSM, AWS KMS, etc.).

### Scaling

- Use PostgreSQL connection pooling.
- Add Redis for rate‑limiting and idempotency key caching.
- Run webhook delivery as a separate Celery task queue.
- Monitor transactions with a blockchain indexer.

## Improvements Implemented

- **Secure Key Management**: Abstract `KeyManager` with mock/KMS/non‑custodial implementations.
- **Idempotency**: Database‑backed idempotency keys for `/payments` endpoint.
- **Atomic Transactions**: Payment flow ensures DB and blockchain consistency.
- **Gas Optimization**: Dynamic gas price estimation (EIP‑1559).
- **Webhook Signing**: HMAC‑SHA256 signatures for secure event delivery.
- **Rate Limiting**: Configurable per‑API‑key limits using Redis.
- **Audit Logging**: Structured logs for all payment attempts.

## Future Roadmap

- Multi‑chain support (Base, Arbitrum, Optimism)
- Gas sponsorship (pay gas in USDC)
- Payment streaming (Sablier‑like)
- Cross‑chain payments (LayerZero, CCIP)
- ZK‑proof identity (privacy‑preserving agents)

## License

MIT