"""Image Generator Provider 抽象 - 根据文本提示生成图片。"""
from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import Any

from ..base import BaseProvider, registry


class BaseImageProvider(BaseProvider):
    type: str = "image"
    requires_gpu: bool = False

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        output_path: Path,
        width: int = 1080,
        height: int = 1080,
        **kwargs: Any,
    ) -> Path:
        """根据 prompt 生成图片到 output_path，返回该路径。"""
        ...

    def get_config_schema(self) -> dict[str, Any]:
        return {
            "width": {"type": "int", "default": 1080, "min": 256, "max": 2048},
            "height": {"type": "int", "default": 1080, "min": 256, "max": 2048},
            "steps": {"type": "int", "default": 30, "min": 1, "max": 100,
                       "description": "SDXL 推理步数"},
        }
