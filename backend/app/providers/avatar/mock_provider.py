"""Mock Avatar Provider - 不依赖 GPU，用 ffmpeg 生成占位视频。"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from ..base import registry
from .base import BaseAvatarProvider


@registry.register
class MockAvatarProvider(BaseAvatarProvider):
    name = "mock"
    requires_gpu = False

    async def render(
        self,
        audio_path: Path,
        portrait_path: Path,
        output_path: Path,
        background_path: Path | None = None,
    ) -> Path:
        """生成一个固定大小的占位 mp4（含音频）。"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        bg_color = "0x1a1a2e"
        # 用 ffmpeg 生成纯色视频，并把音频合并进去
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c={bg_color}:s=720x1280:d=30:r=30",
            "-i", str(audio_path),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest",
            "-movflags", "+faststart",
            str(output_path),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        return output_path

    async def register_portrait(self, portrait_path: Path, name: str) -> str:
        return f"mock_avatar_{name}"

    async def health_check(self) -> bool:
        return True

    async def _ping(self) -> None:
        return None
