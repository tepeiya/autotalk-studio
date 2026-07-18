"""GPT-SoVITS Provider - 仅需 1 分钟样本即可高质量克隆。

约定自部署 HTTP 服务接口：
- POST /clone body={"audio_path","name"} → {"voice_id"}
- POST /synthesize body={"text","voice_id","speed","output_path"} → {"audio_path"}
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from ..base import registry
from .base import BaseTTSProvider


@registry.register
class GPTSoVITSProvider(BaseTTSProvider):
    name = "gptsovits"
    requires_gpu = True

    def __init__(self, base_url: str = "http://127.0.0.1:9880", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=300.0)

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: Path,
        speed: float = 1.0,
        pitch: float = 0.0,
    ) -> Path:
        resp = await self._client.post(
            "/synthesize",
            json={
                "text": text,
                "voice_id": voice_id,
                "speed": speed,
                "output_path": str(output_path),
            },
        )
        resp.raise_for_status()
        data = resp.json()
        out = data.get("audio_path")
        return Path(out) if out else output_path

    async def clone_voice(self, sample_path: Path, name: str) -> str:
        resp = await self._client.post(
            "/clone",
            json={"audio_path": str(sample_path), "name": name},
        )
        resp.raise_for_status()
        return resp.json()["voice_id"]

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/health")
            return resp.status_code == 200
        except Exception:
            return False
