import pytest
from agnostic_llm import *
from agnostic_llm.providers.mock import MockLLM
from agnostic_llm.providers.anthropic_provider import to_anthropic
from agnostic_llm.providers.openai_provider import to_openai
from agnostic_llm.providers.copilot_provider import to_copilot_prompt

TOOL = ToolSpec("add", "d", {"type": "object", "properties": {}}, fn=lambda **k: 5)
HIST = [Message("system", "be brief"), Message("user", "hi"),
        Message("assistant", "", [ToolCall("a", "add", {"x": 1}), ToolCall("b", "add", {"x": 2})]),
        Message("tool", "1", tool_call_id="a"), Message("tool", "2", tool_call_id="b")]


def test_anthropic_conversion():
    system, msgs, tools = to_anthropic(HIST, [TOOL])
    assert system == "be brief" and tools[0]["input_schema"]
    assert msgs[1]["content"][0]["type"] == "tool_use"
    assert len(msgs[2]["content"]) == 2  # both tool results merged into one user turn


def test_openai_conversion():
    msgs, tools = to_openai(HIST, [TOOL])
    assert msgs[0]["role"] == "system"
    assert msgs[2]["tool_calls"][0]["function"]["arguments"] == '{"x": 1}'
    assert msgs[3]["role"] == "tool" and tools[0]["type"] == "function"


def test_fallback():
    llm = FallbackLLM([MockLLM([RateLimitError("x")]), MockLLM(["ok"])], retries=0)
    assert llm.ask("hi") == "ok"


def test_no_fallback_on_all_failing():
    with pytest.raises(LLMError):
        FallbackLLM([MockLLM([AuthError("x")])], retries=0).ask("hi")


def test_agent_loop():
    m = MockLLM([LLMResponse(tool_calls=[ToolCall("1", "add", {})], stop_reason="tool_calls"), "done"])
    text, hist = run_agent(m, "go", [TOOL])
    assert text == "done" and hist[-2].role == "tool"


def test_config_routes():
    cfg = {"models": {"a": {"provider": "mock", "script": ["A"]}, "b": {"provider": "mock", "script": ["B"]}},
           "routes": {"default": ["a", "b"]}}
    assert Models(cfg).get("default").ask("x") == "A"
    assert Models(cfg).get("b").ask("x") == "B"


def test_copilot_prompt_conversion():
    prompt, system = to_copilot_prompt([
        Message("system", "Be concise."),
        Message("user", "Hello"),
        Message("assistant", "Hi there"),
    ])
    assert system == "Be concise."
    assert "User: Hello" in prompt
    assert "Assistant: Hi there" in prompt
