"""Mock TTS Provider - 不依赖外部 API，生成空 WAV 文件用于演示。"""
from __future__ import annotations

import struct
import wave
from pathlib import Path
from typing import Any

from ..base import registry
from .base import BaseTTSProvider


@registry.register
class MockTTSProvider(BaseTTSProvider):
    name = "mock"
    requires_gpu = False

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: Path,
        speed: float = 1.0,
        pitch: float = 0.0,
    ) -> Path:
        """生成一个固定时长的静音 WAV（按文字长度估算时长）。"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        duration = max(1.0, len(text) / 5.0)  # 粗略：5 字/秒
        sample_rate = 16000
        num_frames = int(duration * sample_rate)
        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            # 写入静音帧（这里不生成真实音频，仅占位）
            frames = struct.pack("<" + "h" * 1024, *([0] * 1024))
            for _ in range(0, num_frames, 1024):
                wf.writeframes(frames)
        return output_path

    async def list_voices(self) -> list[dict[str, Any]]:
        return [
            {"id": "mock_male", "name": "Mock 男声", "lang": "zh"},
            {"id": "mock_female", "name": "Mock 女声", "lang": "zh"},
        ]

    async def health_check(self) -> bool:
        return True

    async def _ping(self) -> None:
        return None
