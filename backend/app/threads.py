import json
import re
from collections import defaultdict, deque
from time import time

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from fpdf import FPDF
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.agent import build_graph, run_agent
from app.auth import get_current_user
from app.crypto import decrypt
from app.db import SessionLocal, get_db
from app.models import LLMConfig, Message, Thread, User
from app.schemas import MessageOut, SendMessageIn, ThreadOut

router = APIRouter(prefix="/threads", tags=["threads"])

RATE_LIMIT = 10  # messages per window, independent of credit balance
RATE_WINDOW = 60  # seconds
_recent_sends: dict[str, deque] = defaultdict(deque)  # ponytail: in-memory per-replica; move to Redis if scaled out


def _check_rate_limit(user_id: str) -> None:
    now = time()
    q = _recent_sends[user_id]
    while q and now - q[0] > RATE_WINDOW:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        raise HTTPException(429, f"Rate limit exceeded — max {RATE_LIMIT} messages per minute. Wait a moment.")
    q.append(now)


def _thread_or_404(db: Session, thread_id: str, user: User) -> Thread:
    thread = db.get(Thread, thread_id)
    if thread is None or thread.user_id != user.id or thread.deleted:
        raise HTTPException(404, "Thread not found")
    return thread


@router.get("", response_model=list[ThreadOut])
def list_threads(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    threads = db.query(Thread).filter(Thread.user_id == user.id, Thread.deleted == False).order_by(Thread.created_at.desc()).all()  # noqa: E712
    return [ThreadOut(id=t.id, title=t.title, model=t.model, created_at=t.created_at.isoformat()) for t in threads]


@router.post("", response_model=ThreadOut)
def create_thread(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cfg = db.query(LLMConfig).filter(LLMConfig.user_id == user.id).one_or_none()
    if cfg is None:
        raise HTTPException(400, "Add your LLM API key in Settings before starting a chat")
    thread = Thread(user_id=user.id, model=cfg.model)
    db.add(thread)
    db.commit()
    return ThreadOut(id=thread.id, title=thread.title, model=thread.model, created_at=thread.created_at.isoformat())


@router.delete("/{thread_id}", status_code=204)
def delete_thread(thread_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    thread = _thread_or_404(db, thread_id, user)
    thread.deleted = True  # soft delete: stays in Stats, vanishes from the chat list
    db.commit()


def _pdf_text(s: str) -> str:
    s = s.encode("latin-1", "replace").decode("latin-1")  # ponytail: core PDF fonts are latin-1; embed a TTF if non-Latin scripts matter
    return re.sub(r"(\S{60})(?=\S)", r"\1 ", s)  # break long tokens (URLs); fpdf raises on words wider than the page


@router.get("/{thread_id}/messages/{message_id}/pdf")
def message_pdf(thread_id: str, message_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    thread = _thread_or_404(db, thread_id, user)
    msg = db.get(Message, message_id)
    if msg is None or msg.thread_id != thread.id:
        raise HTTPException(404, "Message not found")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)  # always plain black-on-white, regardless of app theme
    pdf.set_font("helvetica", "", 11)
    try:
        # ponytail: minimal markdown→PDF (headings, bullets, paragraphs); swap in weasyprint if fidelity matters
        for raw in msg.content.splitlines():
            line = re.sub(r"(\*\*|__|`)", "", raw.strip())
            if not line:
                pdf.ln(3)
                continue
            if m := re.match(r"^(#{1,4})\s+(.*)", line):
                pdf.set_font("helvetica", "B", max(12, 19 - 2 * len(m.group(1))))
                pdf.multi_cell(0, 8, _pdf_text(m.group(2)))
                pdf.set_font("helvetica", "", 11)
            elif re.match(r"^[-*]\s+", line):
                pdf.set_x(pdf.l_margin + 4)
                pdf.multi_cell(0, 6, _pdf_text("- " + re.sub(r"^[-*]\s+", "", line)))
            else:
                pdf.multi_cell(0, 6, _pdf_text(line))
    except Exception as exc:  # noqa: BLE001 - a failed render must return through CORS middleware, not a bare 500
        raise HTTPException(500, f"PDF generation failed: {exc}")

    return Response(
        bytes(pdf.output()),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="micromanus-report.pdf"'},
    )


@router.get("/{thread_id}/messages", response_model=list[MessageOut])
def get_messages(thread_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    thread = _thread_or_404(db, thread_id, user)
    return [
        MessageOut(
            id=m.id,
            role=m.role,
            content=m.content,
            input_tokens=m.input_tokens,
            output_tokens=m.output_tokens,
            cache_read_tokens=m.cache_read_tokens,
            cache_write_tokens=m.cache_write_tokens,
            created_at=m.created_at.isoformat(),
        )
        for m in thread.messages
    ]


@router.post("/{thread_id}/messages")
def send_message(thread_id: str, body: SendMessageIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_rate_limit(user.id)
    thread = _thread_or_404(db, thread_id, user)
    cfg = db.query(LLMConfig).filter(LLMConfig.user_id == user.id).one_or_none()
    if cfg is None:
        raise HTTPException(400, "Add your LLM API key in Settings before chatting")

    result = db.execute(update(User).where(User.id == user.id, User.credits > 0).values(credits=User.credits - 1))
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(402, "Out of credits")

    if thread.title == "New chat":
        thread.title = body.content.strip()[:60] or "New chat"
        db.commit()

    user_msg = Message(thread_id=thread.id, role="user", content=body.content)
    db.add(user_msg)
    db.commit()

    history = list(thread.messages[:-1])  # exclude the just-added user message; run_agent appends it fresh
    api_key = decrypt(cfg.encrypted_api_key)
    graph, llm = build_graph(cfg, api_key)
    thread_pk, user_pk = thread.id, user.id
    db.close()  # release the pooled connection; the stream below can run for minutes and uses short-lived sessions

    def event_stream():
        saved_msg_id = None
        try:
            for event in run_agent(graph, history, body.content, wrapup_llm=llm):
                if event["type"] == "usage" and saved_msg_id is not None:
                    with SessionLocal() as s:
                        s.execute(
                            update(Message)
                            .where(Message.id == saved_msg_id)
                            .values(
                                input_tokens=event["input_tokens"],
                                output_tokens=event["output_tokens"],
                                cache_read_tokens=event["cache_read_tokens"],
                                cache_write_tokens=event["cache_write_tokens"],
                            )
                        )
                        s.commit()
                elif event["type"] == "answer":
                    with SessionLocal() as s:
                        msg = Message(thread_id=thread_pk, role="assistant", content=event["content"])
                        s.add(msg)
                        s.commit()
                        saved_msg_id = msg.id
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:  # noqa: BLE001 - surface any tool/LLM failure to the client
            if saved_msg_id is None:
                with SessionLocal() as s:
                    s.execute(update(User).where(User.id == user_pk).values(credits=User.credits + 1))
                    s.commit()
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
