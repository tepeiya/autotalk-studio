"""OpenAI 兼容 Provider（也支持 one-api / 通义兼容模式 / 任何 OpenAI 协议服务）。"""
from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from ..base import registry
from .base import BaseLLMProvider, DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_TEMPLATE
from ...core.schemas import ScriptRequest, ScriptResult


@registry.register
class OpenAILLMProvider(BaseLLMProvider):
    name = "openai"

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        temperature: float = 0.8,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url) if api_key else None

    async def generate_script(self, request: ScriptRequest) -> ScriptResult:
        if self._client is None:
            raise RuntimeError("OpenAI provider 未配置 api_key")

        ref_section = f"参考对标文案：\n{request.reference_text}" if request.reference_text else ""
        user_msg = DEFAULT_USER_TEMPLATE.format(
            topic=request.topic,
            style=request.style,
            duration_sec=request.duration_sec,
            language=request.language,
            reference_section=ref_section,
        )

        resp = await self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=self.temperature,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        return self._parse(content)

    async def _ping(self) -> None:
        if self._client is None:
            raise RuntimeError("no client")
        await self._client.models.list()

    @staticmethod
    def _parse(content: str) -> ScriptResult:
        # 容错：模型偶尔会带 markdown 包裹
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].lstrip()
        data = json.loads(text)
        return ScriptResult(**data)
