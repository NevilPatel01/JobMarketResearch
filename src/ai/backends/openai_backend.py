"""OpenAI backend - cloud API."""

import os
from typing import List, Dict

from .base import LLMBackend


class OpenAIBackend(LLMBackend):
    """Use OpenAI API. Requires OPENAI_API_KEY."""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set in .env")

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key)
        r = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return (r.choices[0].message.content or "").strip()
