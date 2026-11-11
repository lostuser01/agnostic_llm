"""Runs with no API keys (mock models) so you can see the plumbing work."""
from agnostic_llm import *
from agnostic_llm.providers.mock import MockLLM

# 1) Fallback: first model is down, second answers
flaky = MockLLM([ProviderUnavailable("503")], name="primary")
backup = MockLLM(["Hello from the backup model!"], name="backup")
llm = FallbackLLM([flaky, backup], retries=0)
print(llm.ask("hi"), "<-", llm.name)

# 2) Tool loop, identical code regardless of provider
add = ToolSpec("add", "Add two numbers",
               {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                "required": ["a", "b"]}, fn=lambda a, b: a + b)
scripted = MockLLM([LLMResponse(tool_calls=[ToolCall("1", "add", {"a": 2, "b": 3})], stop_reason="tool_calls"),
                    "2 + 3 = 5"])
print(run_agent(scripted, "what is 2+3?", [add])[0])

# 3) Evals across models
run_evals({"a": MockLLM(["42"]), "b": MockLLM(["no idea"])}, [Case("meaning of life?", lambda o: "42" in o)])
