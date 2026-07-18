"""通义千问 Provider - 走 DashScope OpenAI 兼容模式。"""
from __future__ import annotations

from typing import Any

from ..base import registry
from .openai_provider import OpenAILLMProvider


@registry.register
class QwenLLMProvider(OpenAILLMProvider):
    name = "qwen"

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        model: str = "qwen-max",
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
