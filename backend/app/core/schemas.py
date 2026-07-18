"""Pydantic 数据模型 - 业务对象。"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ────────────────────────────────
# 枚举
# ────────────────────────────────


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VideoOrientation(str, Enum):
    PORTRAIT = "portrait"   # 9:16 1080x1920
    LANDSCAPE = "landscape"  # 16:9 1920x1080
    SQUARE = "square"      # 1:1 1080x1080


# ────────────────────────────────
# LLM 台词
# ────────────────────────────────


class ScriptRequest(BaseModel):
    topic: str = Field(..., description="视频主题或关键词")
    style: str = Field("informative", description="文案风格：informative / humorous / emotional / sales")
    duration_sec: int = Field(60, ge=10, le=600)
    language: str = Field("zh", description="zh / en / ja / ko ...")
    reference_text: str | None = Field(None, description="对标文案（少样本仿写）")


class Shot(BaseModel):
    index: int
    text: str
    duration_sec: float = 5.0
    visual_prompt: str | None = None  # 背景图/视频生成提示词


class ScriptResult(BaseModel):
    title: str
    full_text: str
    shots: list[Shot]
    tags: list[str] = []


# ────────────────────────────────
# 声音
# ────────────────────────────────


class VoiceCloneRequest(BaseModel):
    name: str = Field(..., description="克隆音色名称")
    sample_path: str = Field(..., description="参考音频文件路径")
    description: str | None = None


class VoiceProfile(BaseModel):
    id: str
    name: str
    provider: str  # edge / cosyvoice / gptsovits / indextts
    sample_path: str | None = None
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SynthesizeRequest(BaseModel):
    text: str
    voice_id: str
    speed: float = 1.0
    pitch: float = 0.0


# ────────────────────────────────
# 数字人形象
# ────────────────────────────────


class AvatarProfile(BaseModel):
    id: str
    name: str
    provider: str  # musetalk / wav2lip / heygem
    portrait_path: str  # 主播形象图或视频
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AvatarRenderRequest(BaseModel):
    audio_path: str
    avatar_id: str
    background_path: str | None = None  # 可选换背景


# ────────────────────────────────
# 媒体
# ────────────────────────────────


class MediaItem(BaseModel):
    id: str
    type: str  # bgm / background
    name: str
    path: str
    tags: list[str] = []


# ────────────────────────────────
# Project / Task
# ────────────────────────────────


class ProjectCreate(BaseModel):
    name: str
    topic: str
    style: str = "informative"
    duration_sec: int = 60
    language: str = "zh"
    orientation: VideoOrientation = VideoOrientation.PORTRAIT

    # 各阶段 Provider 选择（留空用默认）
    llm_provider: str | None = None
    tts_provider: str | None = None
    voice_id: str | None = None
    avatar_provider: str | None = None
    avatar_id: str | None = None

    # 媒体配置
    bgm_mode: str = "random"  # random / specified / none
    bgm_id: str | None = None
    bg_mode: str = "template"  # template / generated / none

    reference_text: str | None = None  # 对标文案仿写
    auto_publish: bool = False
    publish_platforms: list[str] = []  # ["douyin", "bilibili", "kuaishou"]


class Project(ProjectCreate):
    id: str
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0  # 0.0 ~ 1.0
    current_stage: str | None = None
    script: ScriptResult | None = None
    output_path: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TaskEvent(BaseModel):
    project_id: str
    stage: str  # script / voice / avatar / media / video / publish
    status: TaskStatus
    progress: float = 0.0
    message: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ────────────────────────────────
# Provider 元信息
# ────────────────────────────────


class ProviderInfo(BaseModel):
    name: str
    type: str  # llm / tts / avatar / media / publisher
    requires_gpu: bool = False
    available: bool = True
    config_schema: dict[str, Any] = {}
