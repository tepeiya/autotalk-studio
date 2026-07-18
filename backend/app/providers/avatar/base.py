"""数字人 Avatar Provider 抽象。

输入：音频 + 主播形象（图片/视频）+ 可选背景
输出：口播视频（口型同步）
"""
from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import Any

from ..base import BaseProvider, registry


class BaseAvatarProvider(BaseProvider):
    type: str = "avatar"
    requires_gpu = True

    @abstractmethod
    async def render(
        self,
        audio_path: Path,
        portrait_path: Path,
        output_path: Path,
        background_path: Path | None = None,
    ) -> Path:
        """根据音频驱动主播形象生成口播视频。"""
        ...

    async def register_portrait(self, portrait_path: Path, name: str) -> str:
        """注册一个主播形象，返回 avatar_id。默认返回路径作为 ID。"""
        return str(portrait_path)

    def get_config_schema(self) -> dict[str, Any]:
        return {
            "portrait_path": {"type": "string", "description": "主播形象图/视频路径"},
            "background_path": {"type": "string", "description": "可选背景替换"},
        }
