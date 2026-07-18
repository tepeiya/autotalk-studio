"""应用配置：基于 Pydantic Settings，环境变量 + YAML 双源。"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class LLMConfig(BaseModel):
    default_provider: str = "openai"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    ollama_base_url: str = "http://127.0.0.1:11434/v1"
    ollama_model: str = "qwen2.5:7b"
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_api_key: str = ""
    qwen_model: str = "qwen-max"


class TTSConfig(BaseModel):
    default_provider: str = "edge"
    edge_voice: str = "zh-CN-XiaoxiaoNeural"
    cosyvoice_base_url: str = "http://127.0.0.1:9880"
    gptsovits_base_url: str = "http://127.0.0.1:9880"
    indextts_base_url: str = "http://127.0.0.1:8000"


class AvatarConfig(BaseModel):
    default_provider: str = "musetalk"
    musetalk_base_url: str = "http://127.0.0.1:8080"
    wav2lip_base_url: str = "http://127.0.0.1:8081"
    heygem_base_url: str = "http://127.0.0.1:8082"


class MediaConfig(BaseModel):
    bgm_dir: str = "storage/bgm"
    background_dir: str = "storage/backgrounds"
    default_bgm_mode: str = "random"  # random / specified / none
    default_bg_mode: str = "template"


class PublisherConfig(BaseModel):
    default_provider: str = "dummy"


class PipelineConfig(BaseModel):
    max_concurrent_shots: int = 4
    shot_parallel: bool = True
    output_resolution: str = "1080x1920"  # 竖屏 9:16


class Settings(BaseSettings):
    """主配置：环境变量优先，YAML 提供默认。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    storage_root: str = str(PROJECT_ROOT / "storage")

    llm: LLMConfig = Field(default_factory=LLMConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    avatar: AvatarConfig = Field(default_factory=AvatarConfig)
    media: MediaConfig = Field(default_factory=MediaConfig)
    publisher: PublisherConfig = Field(default_factory=PublisherConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)

    @classmethod
    def load(cls, yaml_path: Path | None = None) -> "Settings":
        """先读 YAML 默认，再用环境变量覆盖。"""
        settings = cls()
        if yaml_path is None:
            yaml_path = PROJECT_ROOT / "config" / "config.yaml"
        if yaml_path.exists():
            with open(yaml_path, "r", encoding="utf-8") as f:
                data: dict[str, Any] = yaml.safe_load(f) or {}
            settings = settings._merge_yaml(data)
        return settings

    def _merge_yaml(self, data: dict[str, Any]) -> "Settings":
        for section in ("llm", "tts", "avatar", "media", "publisher", "pipeline"):
            if section in data:
                current = getattr(self, section)
                merged = current.model_copy(update=data[section])
                setattr(self, section, merged)
        if "host" in data:
            self.host = data["host"]
        if "port" in data:
            self.port = data["port"]
        if "storage_root" in data:
            self.storage_root = data["storage_root"]
        if "cors_origins" in data:
            self.cors_origins = data["cors_origins"]
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def storage_path(self) -> Path:
        p = Path(self.storage_root)
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings.load()
