import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, default="")
    avatar_url: Mapped[str] = mapped_column(String, default="")
    provider: Mapped[str] = mapped_column(String)
    credits: Mapped[int] = mapped_column(Integer, default=0)
    coupon_redeemed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    llm_config: Mapped["LLMConfig"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    threads: Mapped[list["Thread"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def has_access(self) -> bool:
        return self.credits > 0 or self.coupon_redeemed or len(self.payments) > 0


class LLMConfig(Base):
    __tablename__ = "llm_configs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    provider: Mapped[str] = mapped_column(String)
    base_url: Mapped[str] = mapped_column(String)
    encrypted_api_key: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    user: Mapped["User"] = relationship(back_populates="llm_config")


class Thread(Base):
    __tablename__ = "threads"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String, default="New chat")
    model: Mapped[str] = mapped_column(String)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)  # soft delete: hidden from chat, kept for stats
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="threads")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    thread_id: Mapped[str] = mapped_column(ForeignKey("threads.id"), index=True)
    role: Mapped[str] = mapped_column(String)  # user | assistant | tool_event
    content: Mapped[str] = mapped_column(Text)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_write_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    thread: Mapped["Thread"] = relationship(back_populates="messages")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (UniqueConstraint("stripe_session_id", name="uq_payment_session"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    stripe_session_id: Mapped[str] = mapped_column(String, unique=True)
    amount: Mapped[int] = mapped_column(Integer)  # cents
    status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="payments")
