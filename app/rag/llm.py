from __future__ import annotations

from typing import Any

from openai import OpenAI

from app.infrastructure.config import API_KEY, BASE_URL, LANGUAGE_MODEL_NAME
from app.infrastructure.tracing import maybe_wrap_openai, traceable


class OpenAIChatBackend:
    def __init__(self, model_name: str | None = None):
        if not API_KEY:
            raise RuntimeError("Missing API key (SCADS_API_KEY / OPENAI_API_KEY).")

        # Check if using Moonshot AI
        if LANGUAGE_MODEL_NAME.startswith("kimi") or LANGUAGE_MODEL_NAME.startswith("moonshot"):
            # Moonshot AI requires specific base URL and API key format
            base_url = "https://api.moonshot.cn/v1"
            self.client = maybe_wrap_openai(OpenAI(base_url=base_url, api_key=API_KEY))
        else:
            # Default OpenAI-compatible API
            self.client = maybe_wrap_openai(OpenAI(base_url=BASE_URL, api_key=API_KEY))
            
        self.model_name = model_name or LANGUAGE_MODEL_NAME

    @traceable(name="openai_chat_generate", run_type="llm")
    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str = "Return exactly the requested output.",
        temperature: float = 0.2,
        response_format: dict[str, Any] | None = None,
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

        response = self.client.chat.completions.create(**request)

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Model returned empty content.")

        return content
