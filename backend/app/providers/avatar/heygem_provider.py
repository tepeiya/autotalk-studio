"""HeyGem Provider - 商业级数字人方案，集成在 LuoGen-agent / AigcPanel 中。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from ..base import registry
from .base import BaseAvatarProvider


@registry.register
class HeyGemProvider(BaseAvatarProvider):
    name = "heygem"

    def __init__(self, base_url: str = "http://127.0.0.1:8082", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=600.0)

    async def render(
        self,
        audio_path: Path,
        portrait_path: Path,
        output_path: Path,
        background_path: Path | None = None,
    ) -> Path:
        resp = await self._client.post(
            "/render",
            json={
                "audio_path": str(audio_path),
                "portrait_path": str(portrait_path),
                "output_path": str(output_path),
                "background_path": str(background_path) if background_path else None,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        out = data.get("video_path")
        return Path(out) if out else output_path

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/health")
            return resp.status_code == 200
        except Exception:
            return False
