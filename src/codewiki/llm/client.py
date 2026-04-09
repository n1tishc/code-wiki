"""LLM client abstraction wrapping litellm for provider-agnostic completions."""

from __future__ import annotations

import os
from typing import Callable

import litellm
from tenacity import retry, stop_after_attempt, wait_exponential

from codewiki.config import LLMConfig

# Suppress litellm's verbose logging by default
litellm.suppress_debug_info = True


class LLMClient:
    """Provider-agnostic LLM client using litellm."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._setup_env()

    def _setup_env(self) -> None:
        """Set environment variables that litellm expects."""
        if self.config.api_key:
            # litellm reads provider-specific env vars
            provider_env_map = {
                "anthropic": "ANTHROPIC_API_KEY",
                "openai": "OPENAI_API_KEY",
            }
            env_var = provider_env_map.get(self.config.provider)
            if env_var and env_var not in os.environ:
                os.environ[env_var] = self.config.api_key

    def _model_id(self) -> str:
        """Build the litellm model string."""
        # litellm expects 'provider/model' for most providers
        # For ollama: 'ollama/modelname', for openai: 'openai/gpt-4o', etc.
        if "/" in self.config.model:
            return self.config.model
        return f"{self.config.provider}/{self.config.model}"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
    ) -> str:
        """Single completion call. Returns the response text."""
        kwargs: dict = {
            "model": self._model_id(),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": self.config.temperature,
        }
        if self.config.api_base:
            kwargs["api_base"] = self.config.api_base

        response = litellm.completion(**kwargs)
        return response.choices[0].message.content

    def complete_streaming(
        self,
        system_prompt: str,
        user_prompt: str,
        callback: Callable[[str], None] | None = None,
    ) -> str:
        """Streaming completion. Returns full text, calls callback per chunk."""
        kwargs: dict = {
            "model": self._model_id(),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": True,
        }
        if self.config.api_base:
            kwargs["api_base"] = self.config.api_base

        response = litellm.completion(**kwargs)
        chunks: list[str] = []
        for chunk in response:
            delta = chunk.choices[0].delta.content or ""
            chunks.append(delta)
            if callback:
                callback(delta)
        return "".join(chunks)
