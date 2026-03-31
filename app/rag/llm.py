from __future__ import annotations

from openai import OpenAI

from app.infrastructure.config import API_KEY, BASE_URL, LANGUAGE_MODEL_NAME


class OpenAIChatBackend:
    def __init__(self, model_name: str | None = None):
        if not API_KEY:
            raise RuntimeError("Missing API key (SCADS_API_KEY / OPENAI_API_KEY).")

        self.client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
        self.model_name = model_name or LANGUAGE_MODEL_NAME

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str = "Return exactly the requested output.",
        temperature: float = 0.2,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Model returned empty content.")

        return content