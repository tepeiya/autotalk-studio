"""Note Generator Provider 抽象 - 生成小红书笔记格式（标题/正文/标签）。"""
from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import Any

from ..base import BaseProvider, registry


class BaseNoteProvider(BaseProvider):
    type: str = "note"

    @abstractmethod
    async def generate_note(
        self,
        title: str,
        body: str,
        tags: list[str],
        output_path: Path,
        **kwargs: Any,
    ) -> Path:
        """生成笔记 markdown 文件到 output_path。"""
        ...

    def get_config_schema(self) -> dict[str, Any]:
        return {
            "format": {"type": "string", "default": "xhs",
                       "options": ["xhs", "markdown"]},
        }
