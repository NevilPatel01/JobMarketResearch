"""Base class for LLM backends - plug-and-play with Ollama, OpenAI, etc."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class LLMBackend(ABC):
    """Abstract LLM backend. Implement for Ollama, OpenAI, Anthropic, etc."""

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> str:
        """
        Send messages and return assistant reply.
        
        Args:
            messages: [{"role": "system"|"user"|"assistant", "content": "..."}, ...]
            temperature: 0 = deterministic, higher = more random
            
        Returns:
            Assistant response text
        """
        pass
