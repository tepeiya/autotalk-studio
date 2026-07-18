"""TTS Provider 抽象基类。

声音克隆统一通过 clone_voice(sample_path, name) 注册一个 voice_id，
之后 synthesize(text, voice_id, ...) 用该 voice_id 合成音频。
"""
from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import Any

from ..base import BaseProvider, registry


class BaseTTSProvider(BaseProvider):
    type: str = "tts"

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: Path,
        speed: float = 1.0,
        pitch: float = 0.0,
    ) -> Path:
        """合成语音到指定路径，返回该路径。"""
        ...

    async def clone_voice(self, sample_path: Path, name: str) -> str:
        """零样本克隆：返回新的 voice_id。

        默认实现：直接用样本路径作为 voice_id，子类可重写为真实训练流程。
        Edge-TTS 这类不支持克隆的，可直接复用默认（voice_id=预设音色名）。
        """
        return str(sample_path)

    async def list_voices(self) -> list[dict[str, Any]]:
        """返回该 Provider 可用的 voice 列表。"""
        return []

    def get_config_schema(self) -> dict[str, Any]:
        return {
            "voice_id": {"type": "string", "description": "已注册的音色 ID 或 Provider 内置预设名"},
            "speed": {"type": "float", "default": 1.0, "min": 0.5, "max": 2.0},
            "pitch": {"type": "float", "default": 0.0, "min": -12, "max": 12},
        }
