from __future__ import annotations

from typing import Any

from openai import OpenAI

from app.infrastructure.config import API_KEY, BASE_URL, LLM_MODEL_NAME
from app.infrastructure.tracing import maybe_wrap_openai, traceable


class OpenAIChatBackend:
    def __init__(self, model_name: str | None = None):
        if not API_KEY:
            raise RuntimeError("Missing API key (SCADS_API_KEY / OPENAI_API_KEY).")

        self.client = maybe_wrap_openai(OpenAI(base_url=BASE_URL, api_key=API_KEY))
        self.model_name = model_name or LLM_MODEL_NAME

    @traceable(name="openai_chat_generate", run_type="llm")
    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str = "Return exactly the requested output.",
        temperature: float = 0.2,
        response_format: dict[str, Any] | None = None,
        max_tokens: int | None = None,
    ) -> str:
        request: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
        }
        if response_format is not None:
            request["response_format"] = response_format
        if max_tokens is not None:
            request["max_tokens"] = max_tokens

        response = self.client.chat.completions.create(**request)

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Model returned empty content.")

        return content
