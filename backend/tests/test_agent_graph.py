"""Unit tests for the LangGraph agent nodes in app.agent.graph, focused on
the fail-closed grading fix and the decide_to_generate routing logic."""

from types import SimpleNamespace

import pytest

from app.agent.graph import decide_to_generate, grade_documents


def _fake_client(content: str | None = None, raise_exc: Exception | None = None):
    async def create(**kwargs):
        if raise_exc is not None:
            raise raise_exc
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


# ── decide_to_generate ──────────────────────────────────────────────

def test_decide_to_generate_writes_when_documents_relevant():
    state = {"documents_relevant": "yes", "iteration_count": 0}
    assert decide_to_generate(state) == "write"


def test_decide_to_generate_rewrites_when_not_relevant_and_under_limit():
    state = {"documents_relevant": "no", "iteration_count": 1}
    assert decide_to_generate(state) == "rewrite_plan"


def test_decide_to_generate_gives_up_and_writes_at_iteration_limit():
    state = {"documents_relevant": "no", "iteration_count": 3}
    assert decide_to_generate(state) == "write"


# ── grade_documents ──────────────────────────────────────────────────

async def test_grade_documents_returns_no_when_context_is_empty(monkeypatch):
    # No LLM call should even be attempted when there's nothing to grade.
    monkeypatch.setattr("app.agent.graph.get_async_client", lambda: _fake_client())
    state = {"user_query": "what is x", "retrieved_context": [], "iteration_count": 0}
    result = await grade_documents(state)
    assert result["documents_relevant"] == "no"
    assert result["iteration_count"] == 1


async def test_grade_documents_returns_yes_when_llm_says_relevant(monkeypatch):
    monkeypatch.setattr("app.agent.graph.get_async_client", lambda: _fake_client(content="Yes, relevant."))
    state = {
        "user_query": "what is x",
        "retrieved_context": [{"content": "x is a thing"}],
        "iteration_count": 0,
    }
    result = await grade_documents(state)
    assert result["documents_relevant"] == "yes"


async def test_grade_documents_returns_no_when_llm_says_not_relevant(monkeypatch):
    monkeypatch.setattr("app.agent.graph.get_async_client", lambda: _fake_client(content="No."))
    state = {
        "user_query": "what is x",
        "retrieved_context": [{"content": "unrelated text"}],
        "iteration_count": 0,
    }
    result = await grade_documents(state)
    assert result["documents_relevant"] == "no"


async def test_grade_documents_fails_closed_on_llm_exception(monkeypatch):
    """This is the fix from the earlier review: a broken grading call must
    NOT be treated as 'documents are relevant' — it should fail closed."""
    monkeypatch.setattr(
        "app.agent.graph.get_async_client",
        lambda: _fake_client(raise_exc=ConnectionError("LLM provider unreachable")),
    )
    state = {
        "user_query": "what is x",
        "retrieved_context": [{"content": "x is a thing"}],
        "iteration_count": 0,
    }
    result = await grade_documents(state)
    assert result["documents_relevant"] == "no"
    assert result["iteration_count"] == 1


async def test_grade_documents_increments_iteration_count_each_call(monkeypatch):
    monkeypatch.setattr("app.agent.graph.get_async_client", lambda: _fake_client(content="yes"))
    state = {
        "user_query": "q",
        "retrieved_context": [{"content": "c"}],
        "iteration_count": 2,
    }
    result = await grade_documents(state)
    assert result["iteration_count"] == 3
