"""Modular LLM backends - Ollama (local), OpenAI, etc. Plug-and-play.

To add a new backend (e.g. Anthropic):
1. Create backends/anthropic_backend.py implementing LLMBackend.chat()
2. Add case in get_llm_backend() below
3. Set LLM_PROVIDER=anthropic in .env
"""

import os
from typing import Optional

from .base import LLMBackend
from .ollama_backend import OllamaBackend
from .openai_backend import OpenAIBackend


def get_llm_backend(provider: str = None) -> LLMBackend:
    """
    Factory: return LLM backend based on config.
    
    Env: LLM_PROVIDER=ollama|openai (default: ollama)
    
    Returns:
        LLMBackend instance
    """
    provider = (provider or os.getenv("LLM_PROVIDER", "ollama")).lower()
    
    if provider == "ollama":
        return OllamaBackend()
    if provider == "openai":
        return OpenAIBackend()
    
    raise ValueError(
        f"Unknown LLM_PROVIDER={provider}. "
        "Set LLM_PROVIDER=ollama (local) or LLM_PROVIDER=openai (requires OPENAI_API_KEY)."
    )


__all__ = ["LLMBackend", "OllamaBackend", "OpenAIBackend", "get_llm_backend"]
