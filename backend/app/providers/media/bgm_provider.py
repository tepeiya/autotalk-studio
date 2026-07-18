"""BGM Provider - 本地音乐库管理 + 智能选择。

借鉴 Pixelle-Video 的内置 BGM 与 MoneyPrinterTurbo 的随机/指定音乐功能。
"""
from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from ..base import BaseProvider, registry
from ...config import get_settings
from ...core.storage import get_storage


@registry.register
class BGMProvider(BaseProvider):
    name = "bgm"
    type = "media"

    SUPPORTED_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}

    def __init__(self, bgm_dir: str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        s = get_settings()
        self.bgm_dir = Path(bgm_dir) if bgm_dir else (get_storage().root / "bgm")
        self.bgm_dir.mkdir(parents=True, exist_ok=True)

    def list_bgm(self) -> list[dict[str, Any]]:
        items = []
        for p in self.bgm_dir.iterdir():
            if p.suffix.lower() in self.SUPPORTED_EXT:
                items.append({
                    "id": p.stem,
                    "name": p.stem,
                    "path": str(p),
                    "tags": [],
                })
        return items

    def pick(
        self,
        mode: str = "random",
        bgm_id: str | None = None,
        duration_hint_sec: float | None = None,
    ) -> Path | None:
        """选择一首背景音乐。

        mode:
            random   - 随机
            specified - 用 bgm_id 指定
            none     - 不使用
        """
        if mode == "none":
            return None
        items = self.list_bgm()
        if not items:
            return None
        if mode == "specified" and bgm_id:
            for it in items:
                if it["id"] == bgm_id:
                    return Path(it["path"])
            return None
        return Path(random.choice(items)["path"])

    async def health_check(self) -> bool:
        return self.bgm_dir.exists()

    def get_config_schema(self) -> dict[str, Any]:
        return {
            "mode": {"type": "enum", "options": ["random", "specified", "none"], "default": "random"},
            "bgm_id": {"type": "string", "description": "指定音乐 ID（mode=specified 时生效）"},
            "volume": {"type": "float", "default": 0.3, "min": 0, "max": 1},
        }
