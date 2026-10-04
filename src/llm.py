"""Provider wrapper (Google Gemini). Swap this file to change LLM vendors."""
from __future__ import annotations

import os

from google import genai
from google.genai import types

from .config import settings

# Gemini "thinking" tokens count against max_output_tokens. Without headroom, a small
# cap (e.g. query rewriting at 150 tokens) can be used up by thinking and return nothing.
_THINKING_HEADROOM = 2048


class LLMClient:
    def __init__(self, model: str | None = None) -> None:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        self._client = genai.Client(
            api_key=key, http_options=types.HttpOptions(timeout=60_000)  # ms
        )
        self.model = model or settings.llm_model

    @staticmethod
    def _to_contents(messages: list[dict]) -> list[types.Content]:
        """Convert {"role": "user"|"assistant", "content": str} → Gemini contents."""
        return [
            types.Content(
                role="model" if m["role"] == "assistant" else "user",
                parts=[types.Part(text=m["content"])],
            )
            for m in messages
        ]

    def complete(
        self, system: str, messages: list[dict], max_tokens: int | None = None
    ) -> str:
        budget = (max_tokens or settings.max_answer_tokens) + _THINKING_HEADROOM
        resp = self._client.models.generate_content(
            model=self.model,
            contents=self._to_contents(messages),
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=budget,
                temperature=0.0,          # deterministic, best for grounded answers
            ),
        )
        text = (resp.text or "").strip()
        if not text:
            raise RuntimeError(
                "Gemini returned no text (the response may have been blocked by safety filters)."
            )
        return text
