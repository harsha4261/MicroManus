"""Hardcoded model catalog + $/Mtok pricing. Single source of truth for cost math."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    provider: str  # openai | anthropic | kimi
    label: str
    input: float
    output: float
    cache_read: float
    cache_write: float


MODELS: dict[str, ModelInfo] = {
    "gpt-5.1": ModelInfo("openai", "GPT-5.1", input=2.50, output=10.00, cache_read=0.25, cache_write=0.0),
    "gpt-5.1-mini": ModelInfo("openai", "GPT-5.1 Mini", input=0.25, output=1.00, cache_read=0.025, cache_write=0.0),
    "claude-sonnet-5": ModelInfo("anthropic", "Claude Sonnet 5", input=3.00, output=15.00, cache_read=0.30, cache_write=3.75),
    "claude-haiku-4-5": ModelInfo("anthropic", "Claude Haiku 4.5", input=0.80, output=4.00, cache_read=0.08, cache_write=1.00),
    "kimi-k2": ModelInfo("kimi", "Kimi K2", input=0.55, output=2.20, cache_read=0.14, cache_write=0.0),
    # free-tier providers (OpenAI-compatible endpoints, so they work through build_llm's ChatOpenAI fallback)
    "llama-3.3-70b-versatile": ModelInfo("groq", "Llama 3.3 70B (Groq, free)", input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
    "llama-3.1-8b-instant": ModelInfo("groq", "Llama 3.1 8B Instant (Groq, free)", input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
    "openai/gpt-oss-120b": ModelInfo("groq", "GPT-OSS 120B (Groq, free)", input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
    "openai/gpt-oss-20b": ModelInfo("groq", "GPT-OSS 20B (Groq, free)", input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
    "qwen/qwen3-32b": ModelInfo("groq", "Qwen3 32B (Groq, free)", input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
    "deepseek-r1-distill-llama-70b": ModelInfo("groq", "DeepSeek R1 Distill Llama 70B (Groq, free)", input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
    "gemini-2.5-pro": ModelInfo("gemini", "Gemini 2.5 Pro", input=1.25, output=10.00, cache_read=0.0, cache_write=0.0),
    "gemini-2.5-flash": ModelInfo("gemini", "Gemini 2.5 Flash", input=0.30, output=2.50, cache_read=0.0, cache_write=0.0),
    "gemini-2.5-flash-lite": ModelInfo("gemini", "Gemini 2.5 Flash Lite (free tier)", input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
    "gemini-2.0-flash": ModelInfo("gemini", "Gemini 2.0 Flash (free tier)", input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
    "gemini-2.0-flash-lite": ModelInfo("gemini", "Gemini 2.0 Flash Lite (free tier)", input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
    "deepseek/deepseek-chat-v3.1:free": ModelInfo("openrouter", "DeepSeek V3.1 (OpenRouter, free)", input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
    "deepseek/deepseek-r1:free": ModelInfo("openrouter", "DeepSeek R1 (OpenRouter, free)", input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
    "meta-llama/llama-3.3-70b-instruct:free": ModelInfo("openrouter", "Llama 3.3 70B (OpenRouter, free)", input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
    "qwen/qwen-2.5-72b-instruct:free": ModelInfo("openrouter", "Qwen 2.5 72B (OpenRouter, free)", input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
    "mistralai/mistral-7b-instruct:free": ModelInfo("openrouter", "Mistral 7B (OpenRouter, free)", input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
    "google/gemma-2-9b-it:free": ModelInfo("openrouter", "Gemma 2 9B (OpenRouter, free)", input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
    "mistral-large-latest": ModelInfo("mistral", "Mistral Large", input=2.00, output=6.00, cache_read=0.0, cache_write=0.0),
    "mistral-small-latest": ModelInfo("mistral", "Mistral Small (free tier)", input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
    "open-mistral-nemo": ModelInfo("mistral", "Mistral Nemo (free tier)", input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
    "llama3.1-8b": ModelInfo("cerebras", "Llama 3.1 8B (Cerebras, free)", input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
    "llama-3.3-70b": ModelInfo("cerebras", "Llama 3.3 70B (Cerebras, free)", input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
    "qwen-3-32b": ModelInfo("cerebras", "Qwen3 32B (Cerebras, free)", input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
}

PROVIDER_DEFAULT_BASE_URL = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
    "kimi": "https://api.moonshot.ai/v1",
    "groq": "https://api.groq.com/openai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "openrouter": "https://openrouter.ai/api/v1",
    "mistral": "https://api.mistral.ai/v1",
    "cerebras": "https://api.cerebras.ai/v1",
}


def cost_usd(model: str, *, input_tokens: int, output_tokens: int, cache_read_tokens: int, cache_write_tokens: int) -> float:
    info = MODELS.get(model)
    if info is None:
        return 0.0
    # LangChain's input_tokens is the total prompt count *including* cached tokens,
    # so bill only the uncached remainder at the input rate.
    uncached_input = max(0, input_tokens - cache_read_tokens - cache_write_tokens)
    return (
        uncached_input * info.input
        + output_tokens * info.output
        + cache_read_tokens * info.cache_read
        + cache_write_tokens * info.cache_write
    ) / 1_000_000
