"""Edge-TTS Provider - 默认零配置可用，无需 GPU。

注意：Edge-TTS 不支持声音克隆，clone_voice 会回退到使用预设音色名。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import edge_tts

from ..base import registry
from .base import BaseTTSProvider


# 常用预设音色
_EDGE_VOICES = [
    {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓 (女声)", "lang": "zh"},
    {"id": "zh-CN-YunxiNeural", "name": "云希 (男声)", "lang": "zh"},
    {"id": "zh-CN-YunyangNeural", "name": "云扬 (男声)", "lang": "zh"},
    {"id": "zh-CN-XiaoyiNeural", "name": "晓伊 (女声)", "lang": "zh"},
    {"id": "en-US-AriaNeural", "name": "Aria (女声)", "lang": "en"},
    {"id": "en-US-GuyNeural", "name": "Guy (男声)", "lang": "en"},
    {"id": "ja-JP-NanamiNeural", "name": "七海 (女声)", "lang": "ja"},
    {"id": "ko-KR-SunHiNeural", "name": "선히 (女声)", "lang": "ko"},
]


@registry.register
class EdgeTTSProvider(BaseTTSProvider):
    name = "edge"

    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.default_voice = voice

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: Path,
        speed: float = 1.0,
        pitch: float = 0.0,
    ) -> Path:
        voice = voice_id or self.default_voice
        # Edge-TTS rate/format 格式
        rate_str = f"{int((speed - 1) * 100):+d}%"
        pitch_str = f"{int(pitch * 10):+d}Hz"
        communicate = edge_tts.Communicate(text, voice, rate=rate_str, pitch=pitch_str)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        await communicate.save(str(output_path))
        return output_path

    async def clone_voice(self, sample_path: Path, name: str) -> str:
        # Edge-TTS 无克隆能力，直接返回默认音色
        return self.default_voice

    async def list_voices(self) -> list[dict[str, Any]]:
        return _EDGE_VOICES

    async def health_check(self) -> bool:
        return True  # Edge-TTS 始终可用
