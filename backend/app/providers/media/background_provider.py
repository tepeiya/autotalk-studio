"""Background Provider - 背景图/视频素材库 + 模板化背景。

借鉴 Pixelle-Video 的模板系统：static_*.html / image_*.html / video_*.html
MVP 阶段先做素材库随机/指定选择，模板渲染后续接入。
"""
from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from ..base import BaseProvider, registry
from ...core.storage import get_storage


@registry.register
class BackgroundProvider(BaseProvider):
    name = "background"
    type = "media"

    SUPPORTED_IMG = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    SUPPORTED_VID = {".mp4", ".mov", ".webm", ".mkv"}

    def __init__(self, background_dir: str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.background_dir = Path(background_dir) if background_dir else (get_storage().root / "backgrounds")
        self.background_dir.mkdir(parents=True, exist_ok=True)

    def list_backgrounds(self) -> list[dict[str, Any]]:
        items = []
        for p in self.background_dir.iterdir():
            ext = p.suffix.lower()
            kind = None
            if ext in self.SUPPORTED_IMG:
                kind = "image"
            elif ext in self.SUPPORTED_VID:
                kind = "video"
            if kind:
                items.append({
                    "id": p.stem,
                    "name": p.stem,
                    "path": str(p),
                    "type": kind,
                    "tags": [],
                })
        return items

    def pick(
        self,
        mode: str = "template",
        bg_id: str | None = None,
        visual_prompt: str | None = None,
    ) -> Path | None:
        """mode:
            template  - 从本地背景库选
            specified - 用 bg_id 指定
            none      - 不换背景（保留数字人原背景）
        """
        if mode == "none":
            return None
        items = self.list_backgrounds()
        if not items:
            return None
        if mode == "specified" and bg_id:
            for it in items:
                if it["id"] == bg_id:
                    return Path(it["path"])
            return None
        return Path(random.choice(items)["path"])

    async def health_check(self) -> bool:
        return self.background_dir.exists()

    def get_config_schema(self) -> dict[str, Any]:
        return {
            "mode": {"type": "enum", "options": ["template", "specified", "none"], "default": "template"},
            "bg_id": {"type": "string"},
        }
