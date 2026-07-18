from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.db import get_db
from app.models import User

router = APIRouter(prefix="/admin", tags=["admin"])


def is_admin(user: User) -> bool:
    admins = {e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()}
    return user.email.lower() in admins


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not is_admin(user):
        raise HTTPException(403, "Admin access required")
    return user


@router.get("/users")
def list_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "credits": u.credits,
            "coupon_redeemed": u.coupon_redeemed,
            "threads": len(u.threads),
            "paid_usd": sum(p.amount for p in u.payments) / 100,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


class CreditsIn(BaseModel):
    delta: int


@router.post("/users/{user_id}/credits")
def adjust_credits(user_id: str, body: CreditsIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "User not found")
    target.credits = max(0, target.credits + body.delta)
    db.commit()
    return {"credits": target.credits}
