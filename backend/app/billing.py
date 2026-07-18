import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.db import get_db
from app.models import Payment, User

router = APIRouter(prefix="/billing", tags=["billing"])
stripe.api_key = settings.stripe_secret_key


class CouponRequest(BaseModel):
    code: str


@router.post("/coupon")
def redeem_coupon(body: CouponRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.coupon_redeemed:
        raise HTTPException(400, "Coupon already redeemed")
    if body.code.strip() != settings.coupon_code:
        raise HTTPException(400, "Invalid coupon code")
    user.coupon_redeemed = True
    user.credits += settings.signup_credits
    db.commit()
    return {"credits": user.credits}


@router.post("/checkout")
def create_checkout_session(user: User = Depends(get_current_user)):
    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "MicroManus — 5 credits"},
                    "unit_amount": 500,
                },
                "quantity": 1,
            }
        ],
        metadata={"user_id": user.id},
        success_url=f"{settings.frontend_url}/paywall?checkout=success",
        cancel_url=f"{settings.frontend_url}/paywall?checkout=cancelled",
    )
    return {"url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(400, "Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session["metadata"]["user_id"]
        try:
            db.add(Payment(user_id=user_id, stripe_session_id=session["id"], amount=session["amount_total"], status="paid"))
            db.execute(update(User).where(User.id == user_id).values(credits=User.credits + settings.signup_credits))
            db.commit()
        except IntegrityError:
            db.rollback()  # duplicate webhook delivery for the same session — no-op

    return {"received": True}
