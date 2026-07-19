"""Translator Provider 抽象 - 翻译并润色英文内容到中文。"""
from __future__ import annotations

from abc import abstractmethod
from typing import Any

from ..base import BaseProvider, registry


class BaseTranslatorProvider(BaseProvider):
    type: str = "translator"

    @abstractmethod
    async def translate_and_polish(
        self,
        title: str,
        body: str,
        target_lang: str = "zh",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """翻译 + 润色。

        返回 dict:
            title_cn: str         - 翻译润色后标题
            summary_cn: str       - 一句话摘要
            body_cn: str          - 完整润色正文
            key_points: list[str] - 关键点
            tags: list[str]       - 推荐标签
        """
        ...

    def get_config_schema(self) -> dict[str, Any]:
        return {
            "target_lang": {"type": "string", "default": "zh"},
            "style": {"type": "string", "default": "informative",
                      "options": ["informative", "casual", "dramatic", "xhs"]},
        }
