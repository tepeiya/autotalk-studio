"""Ollama Provider - 本地零成本 LLM。

复用 OpenAI 兼容协议，base_url 指向 Ollama 即可。
"""
from __future__ import annotations

from typing import Any

from ..base import registry
from .openai_provider import OpenAILLMProvider


@registry.register
class OllamaLLMProvider(OpenAILLMProvider):
    name = "ollama"

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434/v1",
        model: str = "qwen2.5:7b",
        api_key: str = "ollama",  # Ollama 兼容协议需要任意非空 key
        temperature: float = 0.8,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            **kwargs,
        )
