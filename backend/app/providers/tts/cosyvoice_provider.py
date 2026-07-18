"""CosyVoice Provider - 阿里 FunAudioLLM 出品，零样本克隆。

依赖外部自部署的 CosyVoice HTTP 服务，约定接口：
- POST /clone  body={"audio_path": "...", "name": "..."} → {"voice_id": "..."}
- POST /synthesize body={"text","voice_id","speed","pitch","output_path"} → {"audio_path": "..."}
- GET /voices → [{"id","name","sample_path"}]
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from ..base import registry
from .base import BaseTTSProvider


@registry.register
class CosyVoiceProvider(BaseTTSProvider):
    name = "cosyvoice"
    requires_gpu = True

    def __init__(self, base_url: str = "http://127.0.0.1:9880", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)

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
                "pitch": pitch,
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

    async def list_voices(self) -> list[dict[str, Any]]:
        resp = await self._client.get("/voices")
        resp.raise_for_status()
        return resp.json()

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/health")
            return resp.status_code == 200
        except Exception:
            return False
