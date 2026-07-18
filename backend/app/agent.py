"""LangGraph deep-research agent: think -> tool call -> observe -> repeat.

Built on LangGraph's create_react_agent (matches DrDroid's own LangGraph/OpenAI/Anthropic stack)
rather than a hand-rolled loop, because LangChain normalizes token usage — including
cache-read/cache-write breakdowns — across OpenAI, Anthropic and Moonshot. Hand-rolling would
mean writing a separate usage parser per provider.
"""

import random
import re
from collections.abc import Iterator
from datetime import date
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.errors import GraphRecursionError
from langgraph.prebuilt import create_react_agent

from app.config import settings
from app.models import LLMConfig, Message

SYSTEM_PROMPT_TEMPLATE = """You are MicroManus, an elite deep-research agent with live internet access via the web_search and fetch_page tools. Today's date is {today}. Your training data predates today — for anything recent, factual, or numeric, search first and never answer from memory what you can verify.

Method — work like a top-tier researcher:
1. Decompose the question into the sub-questions that must be answered to cover it properly.
2. Search each angle with specific queries (names, places, dates, technical terms) — not one generic query.
   For anything "recent", "latest", or "current", put today's month and year into the query itself
   (e.g. "California wildfires {today}") and discard results that are clearly about earlier years.
3. Open the most promising results with fetch_page and read the primary source. Search snippets are leads, not evidence.
4. Cross-check important claims across at least two independent sources, and say so when sources disagree.
5. Keep looping think → search → read until the question is genuinely answered or the trail is exhausted.

Reporting:
- For substantive questions, answer as a report in full Markdown: a one-paragraph executive summary first, then clearly headed sections, then a "Sources" section listing every URL you used.
- Cite claims inline with bracketed numbers [1] that match the Sources list.
- Separate evidence (cited) from your own analysis (framed as such). State uncertainty honestly instead of papering over it.
- For simple conversational messages, just reply naturally — no report scaffolding.

Evidence discipline — non-negotiable:
- Never invent statistics, incident names, dates, dollar figures, or document titles. Every number in your answer must appear in a page you actually opened this run, cited [n].
- The Sources list may contain ONLY the URLs you searched or fetched in this conversation — never documents recalled from memory.
- If your research did not surface a fact, write "not found in the sources consulted" — a smaller honest report always beats a fuller invented one.

Reports may be exported as PDF, so keep heading and list structure clean."""

# The model decides when it has enough and stops on its own; this ceiling only catches
# a stuck model looping forever (~24 tool calls before the graceful wrap-up kicks in).
RECURSION_LIMIT = 15

# create_react_agent's hardcoded bail-out when remaining steps can't fit another tool cycle
LANGGRAPH_BUDGET_BAIL = "Sorry, need more steps to process this request."

BUDGET_ERROR = (
    f"This task needed more than the {RECURSION_LIMIT}-step research budget. "
    "Try a narrower question, or split it into parts."
)

WRAPUP_PROMPT = (
    "You have run out of tool-call budget. Using only the information already gathered above, "
    "write your final answer now — in full report format if one was requested, citing only the URLs "
    "you actually read. Do NOT fill gaps with numbers or documents from memory: write "
    "'not found in the sources consulted' for anything unverified."
)

TOOL_FAIL_PROMPT = (
    "Your previous tool call was rejected by the model provider, so no more tools are available. "
    "Answer the question directly now using anything already gathered above. Cite only URLs you "
    "actually read this run, and be explicit about what you could not verify."
)


def _is_tool_call_failure(exc: Exception) -> bool:
    s = str(exc)
    return "tool_use_failed" in s or "Failed to call a function" in s

# Some sites 403 unfamiliar clients; a normal browser UA gets the same public page a person would see.
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def _tavily_search(query: str) -> str | None:
    """Primary search: Tavily's API ranks by freshness far better than scraped DuckDuckGo."""
    try:
        resp = httpx.post(
            "https://api.tavily.com/search",
            json={"api_key": settings.tavily_api_key, "query": query, "max_results": 6},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
    except httpx.HTTPError:
        return None  # fall back to DuckDuckGo
    if not results:
        return None
    return "\n\n".join(f"[{r['title']}]({r['url']})\n{r.get('content', '')[:300]}" for r in results)


@tool
def web_search(query: str) -> str:
    """Search the web for a query and return the top results with titles and URLs."""
    if settings.tavily_api_key and (found := _tavily_search(query)):
        return found
    try:
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=BROWSER_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        return f"Search failed ({exc}). Try rephrasing the query."
    # ponytail: snippets paired to results by order; a result missing its snippet shifts the pairing — parse per-result blocks if that shows up
    snippets = [re.sub("<[^>]+>", "", s).strip() for s in re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.S)]
    results = []
    for i, (href, title) in enumerate(re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', resp.text, re.S)):
        if "uddg=" in href:
            href = unquote(parse_qs(urlparse(href).query).get("uddg", [href])[0])
        snippet = snippets[i] if i < len(snippets) else ""
        results.append((re.sub("<[^>]+>", "", title).strip(), href, snippet))
        if len(results) >= 6:
            break
    if not results:
        return "No results found."
    return "\n\n".join(f"[{t}]({u})\n{s}" if s else f"[{t}]({u})" for t, u, s in results)


MAX_PAGE_CHARS = 400_000  # stop downloading once we have plenty of raw HTML; keeps huge files out of memory


@tool
def fetch_page(url: str) -> str:
    """Fetch a web page by URL and return its readable text content, truncated to ~12000 characters."""
    try:
        with httpx.stream("GET", url, timeout=15, follow_redirects=True, headers=BROWSER_HEADERS) as resp:
            resp.raise_for_status()
            total, parts = 0, []
            for chunk in resp.iter_text():
                parts.append(chunk)
                total += len(chunk)
                if total >= MAX_PAGE_CHARS:
                    break
    except httpx.HTTPError as exc:
        return f"Could not fetch {url} ({exc}). The site may block automated access — use a different source."
    text = re.sub(r"(?is)<(script|style|noscript|svg|nav|header|footer)[^>]*>.*?</\1>", " ", "".join(parts))
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return " ".join(text.split())[:12000]


TOOLS = [web_search, fetch_page]


def build_llm(cfg: LLMConfig, api_key: str):
    # multi-key: comma-separated keys rotate randomly per request to spread provider rate limits
    key = random.choice([k.strip() for k in api_key.split(",") if k.strip()])
    if cfg.provider == "anthropic":
        return ChatAnthropic(model=cfg.model, api_key=key, anthropic_api_url=cfg.base_url)
    # stream_usage keeps usage_metadata populated when responses are token-streamed
    return ChatOpenAI(model=cfg.model, api_key=key, base_url=cfg.base_url, stream_usage=True)


def build_graph(cfg: LLMConfig, api_key: str):
    """Returns (graph, llm) — the raw llm handles the tool-less wrap-up call when the budget runs out."""
    llm = build_llm(cfg, api_key)
    return create_react_agent(llm, TOOLS), llm


def _to_lc_message(m: Message):
    if m.role == "user":
        return HumanMessage(content=m.content)
    if m.role == "assistant":
        return AIMessage(content=m.content)
    return None  # tool_event rows are trace-only, not replayed as context


def _friendly_recursion(stream):
    """Re-raise LangGraph's recursion error with a message fit for the user's screen."""
    try:
        yield from stream
    except GraphRecursionError:
        raise RuntimeError(BUDGET_ERROR) from None


def _chunk_text(content) -> str:
    """Extract plain text from a streamed chunk; Anthropic sends content-block lists, OpenAI plain strings."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def _add_usage(totals: dict[str, int], message: AIMessage) -> None:
    usage = message.usage_metadata or {}
    details = usage.get("input_token_details", {}) or {}
    totals["input_tokens"] += usage.get("input_tokens", 0) or 0
    totals["output_tokens"] += usage.get("output_tokens", 0) or 0
    totals["cache_read_tokens"] += details.get("cache_read", 0) or 0
    totals["cache_write_tokens"] += details.get("cache_creation", 0) or 0


def run_agent(graph, history: list[Message], new_user_content: str, wrapup_llm=None) -> Iterator[dict[str, Any]]:
    """Runs the agent loop, yielding structured trace events for SSE. Last event is 'done'."""
    messages = [SystemMessage(content=SYSTEM_PROMPT_TEMPLATE.format(today=date.today().strftime("%B %d, %Y")))]
    for m in history[-20:]:  # cap replayed context; older turns cost tokens quadratically and rarely matter
        lc = _to_lc_message(m)
        if lc is not None:
            messages.append(lc)
    messages.append(HumanMessage(content=new_user_content))

    usage_totals = {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0, "cache_write_tokens": 0}
    final_text = ""

    def _wrapup(state_messages, prompt: str) -> str:
        result = wrapup_llm.invoke(list(state_messages) + [HumanMessage(content=prompt)])
        _add_usage(usage_totals, result)
        return _chunk_text(result.content) or (result.content if isinstance(result.content, str) else str(result.content))

    last_state = messages
    stream = graph.stream({"messages": messages}, config={"recursion_limit": RECURSION_LIMIT}, stream_mode=["values", "messages"])
    try:
        for mode, payload in _friendly_recursion(stream):
            if mode == "messages":
                chunk, _meta = payload
                if isinstance(chunk, AIMessageChunk):
                    if text := _chunk_text(chunk.content):
                        yield {"type": "delta", "content": text}
                continue

            last_state = payload["messages"]
            last = last_state[-1]

            if isinstance(last, AIMessage):
                _add_usage(usage_totals, last)

                if last.tool_calls:
                    for tc in last.tool_calls:
                        yield {"type": "tool_call", "name": tc["name"], "args": tc["args"]}
                elif last.content:
                    final_text = last.content if isinstance(last.content, str) else str(last.content)
                    if final_text.strip() == LANGGRAPH_BUDGET_BAIL:
                        if wrapup_llm is None:
                            raise RuntimeError(BUDGET_ERROR)
                        # budget exhausted: one final tool-less call answers from what was gathered
                        final_text = _wrapup(last_state[:-1], WRAPUP_PROMPT)
                        yield {"type": "answer", "content": final_text}
                    else:
                        yield {"type": "answer", "content": final_text}

            elif isinstance(last, ToolMessage):
                content = last.content if isinstance(last.content, str) else str(last.content)
                yield {"type": "tool_result", "name": last.name, "content": content[:2000]}
    except Exception as exc:  # noqa: BLE001
        # provider rejected a malformed tool call (common with small models): answer without tools
        if wrapup_llm is None or not _is_tool_call_failure(exc):
            raise
        final_text = _wrapup(last_state, TOOL_FAIL_PROMPT)
        yield {"type": "answer", "content": final_text}

    yield {"type": "usage", **usage_totals}
    yield {"type": "done", "content": final_text}
