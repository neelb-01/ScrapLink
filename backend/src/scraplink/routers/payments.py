import json
import uuid

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy import select

from .. import lots
from ..deps import DB, CurrentUser, EnvDep
from ..errors import Conflict, NotFound
from ..models import PaymentIntent
from ..payments import verify_razorpay_signature
from ..schemas import EscrowOut

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/{intent_id}/simulate-capture", response_model=EscrowOut)
def simulate_capture(intent_id: uuid.UUID, db: DB, env: EnvDep, user: CurrentUser) -> EscrowOut:
    """Stands in for the buyer completing checkout. Only works for simulated-gateway intents."""
    intent = db.get(PaymentIntent, intent_id)
    if intent is None or intent.buyer_id != user.id:
        raise NotFound("payment not found")
    if intent.gateway != "simulated":
        raise Conflict("only simulated payments can be captured this way")
    lots.capture_payment(
        db,
        env,
        intent,
        gateway_payment_id=f"sim_pay_{uuid.uuid4().hex}",
        amount_paise=intent.amount_paise,
    )
    db.commit()
    return _escrow_out(intent)


class CheckoutResultIn(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@router.post("/razorpay/verify", response_model=EscrowOut)
def razorpay_verify(body: CheckoutResultIn, db: DB, env: EnvDep, user: CurrentUser) -> EscrowOut:
    """Checkout's success callback. Lets escrow fund without a public webhook URL (sandbox);
    the webhook stays as the reconciliation path, and capture is idempotent across both."""
    intent = db.scalars(
        select(PaymentIntent).where(PaymentIntent.gateway_order_id == body.razorpay_order_id)
    ).first()
    if intent is None or intent.buyer_id != user.id or intent.gateway != "razorpay":
        raise NotFound("payment not found")
    verify = getattr(env.gateway, "verify_checkout", None)
    if verify is None or not verify(
        body.razorpay_order_id, body.razorpay_payment_id, body.razorpay_signature
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid payment signature")
    # Razorpay enforces payment amount == order amount, so the order amount is authoritative.
    lots.capture_payment(
        db,
        env,
        intent,
        gateway_payment_id=body.razorpay_payment_id,
        amount_paise=intent.amount_paise,
    )
    db.commit()
    return _escrow_out(intent)


def _escrow_out(intent: PaymentIntent) -> EscrowOut:
    return EscrowOut(
        intent_id=intent.id,
        gateway=intent.gateway,
        gateway_order_id=intent.gateway_order_id,
        amount_paise=intent.amount_paise,
        status=intent.status,
    )


@router.post("/razorpay/webhook")
async def razorpay_webhook(request: Request, db: DB, env: EnvDep) -> dict:
    secret = env.settings.razorpay_webhook_secret
    if not secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "webhook secret not configured")
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not verify_razorpay_signature(body, signature, secret):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid signature")

    event = json.loads(body)
    if event.get("event") != "payment.captured":
        return {"status": "ignored"}
    entity = event["payload"]["payment"]["entity"]

    def apply() -> str:
        intent = db.scalars(
            select(PaymentIntent).where(PaymentIntent.gateway_order_id == entity["order_id"])
        ).first()
        if intent is None:
            # Acknowledge so the rail stops retrying an order that is not ours.
            return "unknown_order"
        lots.capture_payment(
            db, env, intent, gateway_payment_id=entity["id"], amount_paise=int(entity["amount"])
        )
        db.commit()
        return "captured"

    return {"status": await run_in_threadpool(apply)}
