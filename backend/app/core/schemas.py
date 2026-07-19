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
    type: str  # llm / tts / avatar / media / publisher / collector / translator / image / note
    requires_gpu: bool = False
    available: bool = True
    config_schema: dict[str, Any] = {}


# ────────────────────────────────
# Reddit 业务线（独立 pipeline）
# ────────────────────────────────


class RedditHotPost(BaseModel):
    """Reddit 采集到的一篇热帖。"""
    post_id: str
    title: str
    selftext: str = ""  # 正文
    subreddit: str
    author: str = ""
    score: int = 0
    num_comments: int = 0
    url: str = ""
    permalink: str = ""
    created_utc: float = 0.0
    collected_at: datetime = Field(default_factory=datetime.utcnow)


class TranslatedPost(BaseModel):
    """翻译润色后的内容。"""
    post_id: str
    original_title: str
    original_text: str
    title_cn: str  # 翻译润色后的标题
    summary_cn: str  # 简短摘要
    body_cn: str  # 完整润色正文
    key_points: list[str] = []  # 关键点提炼
    tags: list[str] = []  # 推荐标签


class RedditImageArtifact(BaseModel):
    """根据帖子内容生成的图片。"""
    post_id: str
    image_path: str
    url: str = ""  # 前端访问 URL
    prompt: str
    width: int = 1080
    height: int = 1080


class RedditNoteArtifact(BaseModel):
    """小红书笔记产物。"""
    post_id: str
    note_path: str  # 笔记 markdown 路径
    url: str = ""  # 前端访问 URL
    title: str  # 小红书标题（≤20字）
    body: str  # 笔记正文（带 emoji + 段落）
    tags: list[str] = []  # #话题
    image_paths: list[str] = []  # 关联图片


class RedditVideoArtifact(BaseModel):
    """复用现有 avatar pipeline 生成的视频。"""
    post_id: str
    video_path: str
    url: str = ""  # 前端访问 URL
    script: ScriptResult | None = None


class RedditTaskCreate(BaseModel):
    """Reddit 业务线任务创建参数。"""
    subreddit: str = Field("interestingasfuck", description="目标 subreddit")
    limit: int = Field(5, ge=1, le=20, description="采集数量")
    time_filter: str = Field("day", description="day/week/month/year/all")
    collector: str = Field("reddit_public", description="采集 provider")
    translator: str = Field("llm", description="翻译 provider")
    image_provider: str = Field("mock", description="图片生成 provider")
    note_provider: str = Field("mock", description="笔记生成 provider")
    generate_image: bool = True
    generate_note: bool = True
    generate_video: bool = False  # 视频较慢，默认不生成
    publish_to_xiaohongshu: bool = False
    xiaohongshu_account: str = "default"


class RedditTaskStatus(str, Enum):
    PENDING = "pending"
    COLLECTING = "collecting"
    TRANSLATING = "translating"
    GENERATING = "generating"
    PUBLISHING = "publishing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RedditTask(BaseModel):
    id: str
    params: RedditTaskCreate
    status: RedditTaskStatus = RedditTaskStatus.PENDING
    progress: float = 0.0
    current_stage: str | None = None
    posts: list[RedditHotPost] = []
    translated: list[TranslatedPost] = []
    images: list[RedditImageArtifact] = []
    notes: list[RedditNoteArtifact] = []
    videos: list[RedditVideoArtifact] = []
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RedditTaskEvent(BaseModel):
    task_id: str
    stage: str  # collect / translate / image / note / video / publish
    status: RedditTaskStatus
    progress: float = 0.0
    message: str | None = None
    post_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
