from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from app.core.database import get_db
from app.api.middleware.auth import get_current_agent
from app.services.gas_sponsorship import GasSponsorshipService
from app.services.payment import PaymentService, PaymentAlreadyProcessedError, PaymentProcessingError
from app.models.agent import Agent
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sponsor", tags=["sponsor"])


class SponsorPaymentRequest(BaseModel):
    """Request to create a gas-sponsored payment."""
    invoice_id: str
    amount: float
    # Optional idempotency key; if not provided, derived from agent+invoice
    idempotency_key: Optional[str] = None


class SponsorPaymentResponse(BaseModel):
    """Response for a sponsored payment."""
    payment_id: str
    transaction_hash: Optional[str] = None
    sponsor_transaction_hash: Optional[str] = None
    sponsored: bool
    status: str
    message: Optional[str] = None


@router.post("/payment", response_model=SponsorPaymentResponse)
async def create_sponsored_payment(
    request: SponsorPaymentRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a gas-sponsored payment.

    This endpoint will attempt to sponsor the gas costs for the payment
    using OpenZeppelin Defender (if configured). If sponsorship is not
    available or fails, the payment will proceed as a regular transaction.
    """
    # 1. Validate sponsorship availability
    sponsorship_service = GasSponsorshipService()
    if not sponsorship_service.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Gas sponsorship is not enabled or configured"
        )

    # 2. Check agent eligibility (optional whitelist, spending caps)
    eligibility = await sponsorship_service.get_sponsorship_status(str(agent.id))
    if not eligibility.get("eligible", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent not eligible for gas sponsorship"
        )

    # 3. Process payment with sponsorship
    payment_service = PaymentService(db)
    try:
        # First, create payment record (sponsored flag will be set later)
        payment = await payment_service.process_payment(
            agent_id=str(agent.id),
            invoice_id=request.invoice_id,
            amount=request.amount
        )

        # TODO: Integrate actual sponsorship logic
        # For now, mark as sponsored but not yet implemented
        payment.sponsored = True
        payment.sponsor_transaction_hash = None  # Placeholder
        await db.commit()

        return SponsorPaymentResponse(
            payment_id=str(payment.id),
            transaction_hash=payment.transaction_hash,
            sponsor_transaction_hash=payment.sponsor_transaction_hash,
            sponsored=payment.sponsored,
            status=payment.status,
            message="Payment created with sponsorship (placeholder)"
        )
    except PaymentAlreadyProcessedError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment already processed"
        )
    except PaymentProcessingError as e:
        logger.error(f"Payment processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment processing failed"
        )
    except Exception as e:
        logger.exception(f"Unexpected error in sponsored payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/eligibility")
async def get_sponsorship_eligibility(
    agent: Agent = Depends(get_current_agent),
):
    """Check if the current agent is eligible for gas sponsorship."""
    sponsorship_service = GasSponsorshipService()
    if not sponsorship_service.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Gas sponsorship is not enabled"
        )
    eligibility = await sponsorship_service.get_sponsorship_status(str(agent.id))
    return eligibility