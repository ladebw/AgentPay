from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routers import agents, wallets, sponsor
from prometheus_client import generate_latest, REGISTRY, Counter, Histogram
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from datetime import datetime
import redis
from sqlalchemy import text
from app.core.database import engine
from app.blockchain import get_blockchain_client
import asyncio
from typing import Dict, Any
app = FastAPI(
    title="AGENTPAY API",
    description="On-Chain Identity + Payment Infrastructure for AI Agents",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
if settings.rate_limit_enabled:
    limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_requests_per_minute}/minute"])
else:
    limiter = Limiter(key_func=get_remote_address, default_limits=[])
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

# Include routers
app.include_router(agents.router, prefix="/api/v1")
app.include_router(wallets.router, prefix="/api/v1")
app.include_router(sponsor.router, prefix="/api/v1")


@app.get("/")
async def root() -> Dict[str, str]:
    return {"message": "AGENTPAY API"}


@app.get("/health")
@limiter.exempt
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for load balancers"""
    try:
        # Check database connection
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        
        # Check Redis connection if configured
        if settings.redis_url:
            redis_client = redis.from_url(settings.redis_url)
            # Ping Redis (sync) in thread pool
            if not await asyncio.to_thread(lambda: redis_client.ping()):
                raise Exception("Redis ping failed")
        
        # Check KMS if configured
        if settings.key_management_mode == "KMS":
            blockchain_client = get_blockchain_client()
            # Quick KMS validation
            if hasattr(blockchain_client.key_manager, 'validate_kms_key'):
                await asyncio.to_thread(blockchain_client.key_manager.validate_kms_key)
        
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.get("/metrics")
@limiter.exempt
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    from prometheus_client import generate_latest
    return Response(
        content=generate_latest(),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )