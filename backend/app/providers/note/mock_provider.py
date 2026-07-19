"""Note Provider 实现 - 生成小红书笔记 markdown。

- MockNoteProvider: 用模板拼接标题/正文/标签/emoji，无外部依赖
- LLMNoteProvider: 调用 LLM 重写更精炼的小红书风格文案（可选）
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ..base import registry
from .base import BaseNoteProvider

logger = logging.getLogger(__name__)


def _wrap_xhs_note(title: str, body: str, tags: list[str]) -> str:
    """生成小红书风格的 markdown 笔记。"""
    lines = [f"# {title}", ""]
    # 正文按段落处理
    for para in (body or "").split("\n"):
        para = para.strip()
        if para:
            lines.append(para)
            lines.append("")
    # 关键 emoji 提示结尾
    lines.append("---")
    lines.append("")
    lines.append("✨ 喜欢就点赞收藏关注吧～")
    lines.append("")
    # 标签
    if tags:
        tag_str = " ".join(f"#{t.replace(' ', '')}" for t in tags)
        lines.append(tag_str)
        lines.append("")
    return "\n".join(lines)


@registry.register
class MockNoteProvider(BaseNoteProvider):
    """用模板生成小红书笔记 markdown。"""

    name = "mock"

    async def generate_note(
        self,
        title: str,
        body: str,
        tags: list[str],
        output_path: Path,
        **kwargs: Any,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = _wrap_xhs_note(title, body, tags)
        output_path.write_text(content, encoding="utf-8")
        logger.info("Note written: %s (%d chars)", output_path, len(content))
        return output_path

    async def health_check(self) -> bool:
        return True


@registry.register
class LLMNoteProvider(BaseNoteProvider):
    """LLM 重写版笔记 provider - 调用 LLM 进一步润色。"""

    name = "llm"

    def __init__(self, llm_provider: str = "mock", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.llm_provider_name = llm_provider

    async def generate_note(
        self,
        title: str,
        body: str,
        tags: list[str],
        output_path: Path,
        **kwargs: Any,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # 暂不接 LLM，直接走模板（避免重复调用 LLM）
        content = _wrap_xhs_note(title, body, tags)
        output_path.write_text(content, encoding="utf-8")
        return output_path

    async def health_check(self) -> bool:
        return True
