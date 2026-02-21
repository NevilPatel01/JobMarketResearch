"""Ollama backend - cloud (Ollama.com) or local. Cloud preferred when OLLAMA_API_KEY is set."""

import os
from typing import List, Dict

from .base import LLMBackend

OLLAMA_CLOUD_HOST = "https://ollama.com"
# Cloud models: llama3.2 not on cloud. Use qwen3-next:80b, ministral-3:8b, etc. See ollama.com/search?c=cloud
OLLAMA_CLOUD_DEFAULT_MODEL = "qwen3-next:80b"
OLLAMA_LOCAL_DEFAULT_MODEL = "llama3.2"


class OllamaBackend(LLMBackend):
    """Use Ollama models. Cloud (ollama.com) when OLLAMA_API_KEY is set; otherwise local."""

    def __init__(self, model: str = None, base_url: str = None, api_key: str = None):
        api_key = api_key or os.getenv("OLLAMA_API_KEY", "").strip()
        default_model = OLLAMA_CLOUD_DEFAULT_MODEL if api_key else OLLAMA_LOCAL_DEFAULT_MODEL
        self.model = model or os.getenv("OLLAMA_MODEL", default_model)
        self.api_key = api_key
        if self.api_key:
            self.host = OLLAMA_CLOUD_HOST
            self.headers = {"Authorization": f"Bearer {self.api_key}"}
        else:
            self.host = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            self.headers = {}

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> str:
        try:
            import ollama
        except ImportError:
            raise ImportError("Install ollama: pip install ollama")

        kwargs = {"host": self.host}
        if self.headers:
            kwargs["headers"] = self.headers
        client = ollama.Client(**kwargs)
        resp = client.chat(model=self.model, messages=messages, options={"temperature": temperature})
        return (resp.get("message", {}).get("content") or "").strip()
