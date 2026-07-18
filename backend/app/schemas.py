from pydantic import BaseModel


class LLMConfigIn(BaseModel):
    provider: str
    model: str
    api_key: str
    base_url: str | None = None


class LLMConfigOut(BaseModel):
    provider: str
    model: str
    base_url: str
    key_set: bool


class ThreadOut(BaseModel):
    id: str
    title: str
    model: str
    created_at: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    created_at: str


class SendMessageIn(BaseModel):
    content: str


class ThreadStats(BaseModel):
    thread_id: str
    title: str
    model: str
    message_count: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost_usd: float
