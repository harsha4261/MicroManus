from langchain_core.messages import AIMessage, AIMessageChunk

from app.agent import _chunk_text, run_agent


class StubGraph:
    """Mimics LangGraph's multi-mode stream: token chunks then the final state."""

    def stream(self, _state, config=None, stream_mode=None):
        assert stream_mode == ["values", "messages"]
        yield ("messages", (AIMessageChunk(content="Hel"), {}))
        yield ("messages", (AIMessageChunk(content="lo"), {}))
        final = AIMessage(
            content="Hello",
            usage_metadata={"input_tokens": 10, "output_tokens": 2, "total_tokens": 12, "input_token_details": {"cache_read": 4}},
        )
        yield ("values", {"messages": [final]})


def test_chunk_text_handles_both_provider_shapes():
    assert _chunk_text("plain") == "plain"
    assert _chunk_text([{"type": "text", "text": "a"}, {"type": "tool_use"}, {"type": "text", "text": "b"}]) == "ab"
    assert _chunk_text(None) == ""


def test_run_agent_streams_deltas_then_answer_and_usage():
    events = list(run_agent(StubGraph(), history=[], new_user_content="hi"))
    types = [e["type"] for e in events]
    assert types == ["delta", "delta", "answer", "usage", "done"]
    assert "".join(e["content"] for e in events if e["type"] == "delta") == "Hello"
    assert events[2]["content"] == "Hello"
    usage = events[3]
    assert usage["input_tokens"] == 10 and usage["output_tokens"] == 2 and usage["cache_read_tokens"] == 4


class ExplodingGraph:
    def stream(self, *_args, **_kwargs):
        from langgraph.errors import GraphRecursionError

        raise GraphRecursionError("Recursion limit of 30 reached")
        yield  # pragma: no cover


def test_recursion_limit_raises_friendly_message():
    import pytest

    with pytest.raises(RuntimeError, match="research budget"):
        list(run_agent(ExplodingGraph(), history=[], new_user_content="hi"))


def test_web_search_pairs_titles_with_snippets(monkeypatch):
    import httpx

    from app.agent import web_search

    html = (
        '<a class="result__a" href="https://a.example">First</a>'
        '<a class="result__snippet">About <b>A</b></a>'
        '<a class="result__a" href="https://b.example">Second</a>'
    )

    class FakeResp:
        text = html

        def raise_for_status(self):
            pass

    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResp())
    out = web_search.invoke({"query": "q"})
    assert "[First](https://a.example)\nAbout A" in out
    assert "[Second](https://b.example)" in out


def test_langgraph_canned_bailout_becomes_budget_error():
    import pytest

    from app.agent import LANGGRAPH_BUDGET_BAIL

    class BailGraph:
        def stream(self, *_args, **_kwargs):
            yield ("values", {"messages": [AIMessage(content=LANGGRAPH_BUDGET_BAIL)]})

    with pytest.raises(RuntimeError, match="research budget"):
        list(run_agent(BailGraph(), history=[], new_user_content="big task"))


def test_budget_bailout_wraps_up_with_toolless_answer():
    from app.agent import LANGGRAPH_BUDGET_BAIL, WRAPUP_PROMPT

    class BailGraph:
        def stream(self, *_args, **_kwargs):
            yield ("values", {"messages": [AIMessage(content=LANGGRAPH_BUDGET_BAIL)]})

    class WrapupLLM:
        def invoke(self, messages):
            assert messages[-1].content == WRAPUP_PROMPT
            assert all(m.content != LANGGRAPH_BUDGET_BAIL for m in messages)
            return AIMessage(
                content="Partial report from gathered sources",
                usage_metadata={"input_tokens": 7, "output_tokens": 3, "total_tokens": 10},
            )

    events = list(run_agent(BailGraph(), history=[], new_user_content="big task", wrapup_llm=WrapupLLM()))
    types = [e["type"] for e in events]
    assert types == ["answer", "usage", "done"]
    assert events[0]["content"] == "Partial report from gathered sources"
    assert events[1]["input_tokens"] == 7 and events[1]["output_tokens"] == 3


def test_web_search_prefers_tavily_when_key_set(monkeypatch):
    import httpx

    from app.agent import web_search
    from app.config import settings

    monkeypatch.setattr(settings, "tavily_api_key", "tvly-test")

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"results": [{"title": "Fresh news", "url": "https://news.example", "content": "today's story"}]}

    calls = {}

    def fake_post(url, **kwargs):
        calls["url"] = url
        assert kwargs["json"]["query"] == "q"
        return FakeResp()

    monkeypatch.setattr(httpx, "post", fake_post)
    out = web_search.invoke({"query": "q"})
    assert calls["url"] == "https://api.tavily.com/search"
    assert "[Fresh news](https://news.example)" in out and "today's story" in out


def test_provider_tool_failure_recovers_with_toolless_answer():
    from app.agent import TOOL_FAIL_PROMPT

    class FailingGraph:
        def stream(self, *_args, **_kwargs):
            yield ("values", {"messages": [AIMessage(content="", tool_calls=[{"name": "web_search", "args": {"query": "x"}, "id": "1"}])]})
            raise Exception(
                "Error code: 400 - {'error': {'message': 'Failed to call a function. Please adjust your prompt.', 'code': 'tool_use_failed'}}"
            )

    class WrapupLLM:
        def invoke(self, messages):
            assert messages[-1].content == TOOL_FAIL_PROMPT
            return AIMessage(content="Direct answer without tools", usage_metadata={"input_tokens": 5, "output_tokens": 2, "total_tokens": 7})

    events = list(run_agent(FailingGraph(), history=[], new_user_content="q", wrapup_llm=WrapupLLM()))
    types = [e["type"] for e in events]
    assert types == ["tool_call", "answer", "usage", "done"]
    assert events[1]["content"] == "Direct answer without tools"


def test_non_tool_failures_still_raise():
    import pytest

    class BrokenGraph:
        def stream(self, *_args, **_kwargs):
            raise Exception("Error code: 401 - invalid api key")
            yield  # pragma: no cover

    class WrapupLLM:
        def invoke(self, messages):  # pragma: no cover
            raise AssertionError("must not be called")

    with pytest.raises(Exception, match="invalid api key"):
        list(run_agent(BrokenGraph(), history=[], new_user_content="q", wrapup_llm=WrapupLLM()))
