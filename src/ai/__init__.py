"""AI module for natural language query. Plug-and-play: Ollama (local) or OpenAI."""

from .query_agent import nl_to_sql_and_validate, generate_sql, validate_query
from .backends import get_llm_backend, LLMBackend, OllamaBackend, OpenAIBackend

__all__ = [
    "nl_to_sql_and_validate",
    "generate_sql",
    "validate_query",
    "get_llm_backend",
    "LLMBackend",
    "OllamaBackend",
    "OpenAIBackend",
]
