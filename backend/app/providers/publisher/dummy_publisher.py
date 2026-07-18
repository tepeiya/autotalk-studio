"""占位 Publisher - 仅复制到 storage/published，留出真实平台接入位。

真实多平台发布（抖音/B站/快手）建议接入：
- social-auto-upload (https://github.com/dreammis/social-auto-upload)
- MediaCrawler 类项目
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..base import registry
from .base import BasePublisher
from ...core.storage import get_storage


@registry.register
class DummyPublisher(BasePublisher):
    name = "dummy"

    async def publish(
        self,
        video_path: Path,
        title: str,
        description: str | None = None,
        tags: list[str] | None = None,
        cover_path: Path | None = None,
    ) -> dict[str, Any]:
        out_dir = get_storage().root / "published"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{title}_{video_path.stem}.mp4"
        # 简单复制
        out_path.write_bytes(video_path.read_bytes())
        return {
            "platform": "local",
            "video_url": str(out_path),
            "title": title,
        }

    async def health_check(self) -> bool:
        return True
