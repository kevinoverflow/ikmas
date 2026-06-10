# LLM Layer

The LLM layer is split into a raw provider backend and a schema-enforcing client.

## OpenAIChatBackend

Location: `app/rag/llm.py`

`OpenAIChatBackend` wraps the OpenAI Python client against an OpenAI-compatible base URL. It reads:

- `API_KEY` from `SCADS_API_KEY` or `OPENAI_API_KEY`
- `BASE_URL` from `OPENAI_BASE_URL`
- default model from `LANGUAGE_MODEL_NAME` or `GLOBAL_MODEL_OVERRIDE`

Primary method:

```python
generate(
    prompt: str,
    *,
    system_prompt: str = "Return exactly the requested output.",
    temperature: float = 0.2,
    response_format: dict[str, Any] | None = None,
    max_tokens: int | None = None,
) -> str
```

It returns raw text and does not validate schemas.

## LLMClient

Location: `app/backend/llm_client.py`

`LLMClient.generate_json(...)` is the backend-facing structured-output layer. It:

1. calls the backend with `response_format={"type": "json_object"}`,
2. parses JSON from raw text or fenced output,
3. normalizes common field variants,
4. validates against `AssistantPayload`,
5. performs one repair call if validation fails,
6. salvages raw text into a valid payload if repair fails,
7. returns a deterministic fallback if all else fails.

## Role Model Selection

`model_selection_for_role(...)` in `router_agent.py` maps active roles to configured model environment variables:

- `SCRIBE_MODEL_NAME`
- `SEMANTIC_LINKING_MODEL_NAME`
- `MENTOR_MODEL_NAME`
- `CONTEXT_RECONSTRUCTOR_MODEL_NAME`
- fallback `LANGUAGE_MODEL_NAME`

The UI can pass `model_override`, which is used for the answering backend.

## Tracing

LLM and orchestration calls are decorated with optional tracing hooks in `app/infrastructure/tracing.py`. Without LangSmith configuration, the app continues normally.
