# agnostic-llm

One interface, any model. Your app talks to `LLM`; adapters talk to vendors.

```bash
pip install -e ".[all]"
cp config.example.yaml config.yaml     # edit models, set API keys as env vars
python -m agnostic_llm "Explain recursion in one line"       # uses route "default"
python -m agnostic_llm -m local "hi"                          # force a model
python examples/demo.py                                       # no keys needed
pytest
```

```python
from agnostic_llm import Models, Message, ToolSpec, run_agent
llm = Models.from_file("config.yaml").get("default")   # Claude -> GPT -> Gemini fallback
print(llm.ask("hello"))
```

## What's here
- `types.py`    neutral Message / ToolSpec / LLMResponse + unified errors
- `providers/`  Anthropic adapter, OpenAI-compatible adapter (OpenAI, Gemini, Ollama, vLLM, OpenRouter...), mock
- `router.py`   retry + automatic fallback across models
- `registry.py` config-driven model selection; `register_provider()` to add Bedrock/Vertex/etc.
- `agent.py`    tool-calling loop that works identically on every provider
- `evals.py`    run the same test cases on every model before you switch

## Adding a provider
Subclass `LLM`, implement `chat()` (convert in, call, convert out, wrap errors with `map_exception`),
then `register_provider("name", YourLLM)`.

## Caveats
Prompts are not fully portable: run `evals.py` on your own cases whenever you change models.
Use `provider_options={...}` to reach provider-only features (prompt caching, thinking) without leaking them into app code.
Model names in `config.example.yaml` are examples; set the ones you actually have access to.
