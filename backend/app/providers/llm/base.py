"""LLM Provider 抽象基类。"""
from __future__ import annotations

from abc import abstractmethod
from typing import Any

from ..base import BaseProvider, registry
from ...core.schemas import ScriptRequest, ScriptResult


class BaseLLMProvider(BaseProvider):
    """LLM 抽象：输入主题/对标文案 → 输出分镜化文案。"""

    type: str = "llm"

    @abstractmethod
    async def generate_script(self, request: ScriptRequest) -> ScriptResult:
        ...

    async def health_check(self) -> bool:
        try:
            await self._ping()
            return True
        except Exception:
            return False

    async def _ping(self) -> None:
        """具体实现可重写：发一次最小调用确认连通性。"""
        return None

    def get_config_schema(self) -> dict[str, Any]:
        return {
            "model": {"type": "string", "default": ""},
            "temperature": {"type": "float", "default": 0.8, "min": 0, "max": 2},
        }


# 默认 Prompt 模板（运行时也可由 config/prompts/ 覆盖）
DEFAULT_SYSTEM_PROMPT = """你是一位资深的短视频脚本编剧。
请根据用户输入的视频主题，创作一段适合口播的解说词，并自动拆分为多个分镜。

要求：
1. 总时长尽量接近用户指定秒数，每个分镜 3-8 秒
2. 文案口语化，适合真人/数字人口播
3. 每个分镜给出 visual_prompt 字段：用于生成背景图/视频的简短描述
4. 输出严格 JSON 格式
"""

DEFAULT_USER_TEMPLATE = """主题：{topic}
风格：{style}
总时长（秒）：{duration_sec}
语言：{language}
{reference_section}
请输出 JSON：
{{
  "title": "视频标题",
  "full_text": "完整文案",
  "shots": [
    {{"index": 1, "text": "分镜台词", "duration_sec": 5.0, "visual_prompt": "背景画面描述"}},
    ...
  ],
  "tags": ["标签1", "标签2"]
}}
"""
