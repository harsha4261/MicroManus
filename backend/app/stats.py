from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Thread, User
from app.pricing import cost_usd
from app.schemas import ThreadStats

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=list[ThreadStats])
def get_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    threads = db.query(Thread).filter(Thread.user_id == user.id).order_by(Thread.created_at.desc()).all()
    out = []
    for t in threads:
        assistant_msgs = [m for m in t.messages if m.role == "assistant"]
        input_tokens = sum(m.input_tokens for m in assistant_msgs)
        output_tokens = sum(m.output_tokens for m in assistant_msgs)
        cache_read = sum(m.cache_read_tokens for m in assistant_msgs)
        cache_write = sum(m.cache_write_tokens for m in assistant_msgs)
        out.append(
            ThreadStats(
                thread_id=t.id,
                title=t.title + (" (deleted)" if t.deleted else ""),
                model=t.model,
                message_count=len(t.messages),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read,
                cache_write_tokens=cache_write,
                cost_usd=cost_usd(
                    t.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cache_read_tokens=cache_read,
                    cache_write_tokens=cache_write,
                ),
            )
        )
    return out
