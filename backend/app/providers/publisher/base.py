"""Publisher 抽象：把生成好的视频发布到抖音/B站/快手等。"""
from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import Any

from ..base import BaseProvider


class BasePublisher(BaseProvider):
    type: str = "publisher"

    @abstractmethod
    async def publish(
        self,
        video_path: Path,
        title: str,
        description: str | None = None,
        tags: list[str] | None = None,
        cover_path: Path | None = None,
    ) -> dict[str, Any]:
        """发布视频，返回平台返回的发布信息（含平台视频 ID/URL）。"""
        ...

    def get_config_schema(self) -> dict[str, Any]:
        return {
            "cookie": {"type": "string", "description": "登录态 cookie"},
        }
