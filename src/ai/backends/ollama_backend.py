"""Ollama backend - local LLM, no API key needed."""

import os
from typing import List, Dict

from .base import LLMBackend


class OllamaBackend(LLMBackend):
    """Use local Ollama models. Run `ollama serve` and pull a model first."""

    def __init__(self, model: str = None, base_url: str = None):
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> str:
        try:
            import ollama
        except ImportError:
            raise ImportError("Install ollama: pip install ollama")

        client = ollama.Client(host=self.base_url)
        resp = client.chat(model=self.model, messages=messages, options={"temperature": temperature})
        return (resp.get("message", {}).get("content") or "").strip()
