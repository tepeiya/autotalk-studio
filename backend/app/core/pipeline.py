"""Pipeline - 端到端编排：文案 → 配音 → 数字人 → 媒体 → 合成 → 发布。

设计要点：
- 每个 Project 触发一个 pipeline 执行
- 分镜级可并行（受 pipeline.max_concurrent_shots 限制）
- 通过回调推送进度事件（SSE/WS）
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Callable

from ..config import get_settings
from ..core.schemas import (
    Project,
    ScriptRequest,
    SynthesizeRequest,
    TaskEvent,
    TaskStatus,
)
from ..core.storage import get_storage
from ..services.avatar_service import avatar_service
from ..services.media_service import media_service
from ..services.script_service import script_service
from ..services.video_service import video_service
from ..services.voice_service import voice_service
from ..utils.ffmpeg_utils import mix_audio_video as _mix_av

logger = logging.getLogger(__name__)

# 进度回调类型
ProgressCallback = Callable[[TaskEvent], None]


@dataclass
class StageProgress:
    name: str
    weight: float  # 该阶段在总进度中的权重


STAGES = [
    StageProgress("script", 0.1),
    StageProgress("voice", 0.25),
    StageProgress("avatar", 0.35),
    StageProgress("media", 0.05),
    StageProgress("video", 0.20),
    StageProgress("publish", 0.05),
]


class Pipeline:
    """单个 Project 的执行管线。"""

    def __init__(self, project: Project, on_event: ProgressCallback | None = None) -> None:
        self.project = project
        self._on_event = on_event
        self._completed_weight = 0.0

    async def run(self) -> Project:
        p = self.project
        try:
            self._emit("script", TaskStatus.RUNNING, 0.0, "开始生成台词")
            p.status = TaskStatus.RUNNING
            p.current_stage = "script"

            # 1) 生成文案
            script = await script_service.generate(
                ScriptRequest(
                    topic=p.topic,
                    style=p.style,
                    duration_sec=p.duration_sec,
                    language=p.language,
                    reference_text=p.reference_text,
                ),
                provider_name=p.llm_provider,
            )
            p.script = script
            self._advance("script", 1.0, f"生成 {len(script.shots)} 个分镜")

            # 2) 并行：每分镜 → 音频 + 背景选择
            storage = get_storage()
            ws = storage.task_workspace(p.id)
            audio_paths: list[Path] = []
            avatar_videos: list[Path] = []

            self._emit("voice", TaskStatus.RUNNING, 0.0, "开始合成配音")
            self._emit("avatar", TaskStatus.RUNNING, 0.0, "开始生成数字人口播")

            shot_count = len(script.shots)
            from ..config import get_settings
            max_conc = get_settings().pipeline.max_concurrent_shots

            sem = asyncio.Semaphore(max_conc)
            completed_voice = 0
            completed_avatar = 0
            lock = asyncio.Lock()

            async def process_shot(idx: int, shot):
                nonlocal completed_voice, completed_avatar
                async with sem:
                    # 配音
                    audio_path = await voice_service.synthesize(
                        SynthesizeRequest(
                            text=shot.text,
                            voice_id=p.voice_id or "",
                            speed=1.0,
                        ),
                        provider_name=p.tts_provider,
                    )
                    audio_paths.append((idx, audio_path))
                    async with lock:
                        completed_voice += 1
                        self._advance(
                            "voice",
                            completed_voice / shot_count,
                            f"配音 {completed_voice}/{shot_count}",
                        )

                    # 数字人
                    if p.avatar_id:
                        bg = media_service.pick_background(
                            mode=p.bg_mode,
                            bg_id=None,
                        )
                        vid = await avatar_service.render(
                            audio_path=audio_path,
                            avatar_id=p.avatar_id,
                            output_path=ws / f"shot_{idx:03d}.mp4",
                            background_path=bg,
                            provider_name=p.avatar_provider,
                        )
                        avatar_videos.append((idx, vid))
                        async with lock:
                            completed_avatar += 1
                            self._advance(
                                "avatar",
                                completed_avatar / shot_count,
                                f"口播 {completed_avatar}/{shot_count}",
                            )
                    else:
                        # 没有数字人时，直接用音频 + 背景作为一段视频
                        bg = media_service.pick_background(mode=p.bg_mode)
                        bgm = media_service.pick_bgm(mode=p.bgm_mode, bgm_id=p.bgm_id)
                        bg_video = bg if bg else await _placeholder_video(
                            ws / f"shot_{idx:03d}_bg.mp4", shot.duration_sec
                        )
                        vid = await _mix_av(
                            video_path=bg_video,
                            audio_path=audio_path,
                            bgm_path=bgm,
                            output_path=ws / f"shot_{idx:03d}.mp4",
                        )
                        avatar_videos.append((idx, vid))

            # 启动并行
            await asyncio.gather(*[process_shot(i, s) for i, s in enumerate(script.shots)])

            # 排序
            audio_paths.sort(key=lambda x: x[0])
            avatar_videos.sort(key=lambda x: x[0])
            audio_paths = [p for _, p in audio_paths]
            avatar_videos = [p for _, p in avatar_videos]

            # 3) 媒体
            self._advance("media", 1.0, "媒体素材就绪")
            bgm_final = media_service.pick_bgm(mode=p.bgm_mode, bgm_id=p.bgm_id)

            # 4) 合成
            self._emit("video", TaskStatus.RUNNING, 0.0, "合成最终视频")
            final = await video_service.compose(
                shot_videos=avatar_videos,
                bgm_path=bgm_final,
                output_path=get_storage().videos_dir / f"{p.id}.mp4",
            )
            p.output_path = str(final)
            self._advance("video", 1.0, "合成完成")

            # 5) 发布（可选）
            if p.auto_publish and p.publish_platforms:
                self._emit("publish", TaskStatus.RUNNING, 0.0, f"开始发布到 {len(p.publish_platforms)} 个平台")
                from ..providers.base import registry as preg
                from ..providers.publisher.social_auto_upload_provider import PLATFORM_MAP
                import os as _os
                sau_path = _os.environ.get("SOCIAL_AUTO_UPLOAD_PATH", "/workspace/social-auto-upload")
                for plat in p.publish_platforms:
                    # 平台路由：dummy 走 dummy；其他都走 social_auto_upload
                    if plat == "dummy":
                        publisher = preg.create("publisher", "dummy")
                        await publisher.publish(
                            video_path=final,
                            title=script.title,
                            tags=script.tags,
                        )
                    elif plat in PLATFORM_MAP:
                        publisher = preg.create_fresh(
                            "publisher", "social_auto_upload",
                            project_path=sau_path,
                        )
                        try:
                            await publisher.publish(
                                video_path=final,
                                title=script.title,
                                tags=script.tags,
                                platform=plat,
                            )
                        except FileNotFoundError as e:
                            # 真实平台未配置 → 记录但不中断 pipeline
                            logger.warning("Publish to %s skipped: %s", plat, e)
                            self._emit("publish", TaskStatus.RUNNING, 0.5, f"{plat} 跳过：{e}")
                            continue
                    else:
                        logger.warning("Unknown publish platform: %s", plat)
                        continue
                self._advance("publish", 1.0, "发布完成")

            p.status = TaskStatus.SUCCESS
            p.progress = 1.0
            p.current_stage = None
            self._emit("done", TaskStatus.SUCCESS, 1.0, "全部完成")
            return p

        except Exception as e:
            logger.exception("Pipeline failed for project %s", p.id)
            p.status = TaskStatus.FAILED
            p.error = str(e)
            self._emit(p.current_stage or "error", TaskStatus.FAILED, p.progress, str(e))
            return p

    def _advance(self, stage: str, ratio: float, message: str | None = None) -> None:
        """推进某阶段进度。"""
        total = 0.0
        for s in STAGES:
            if s.name == stage:
                total += s.weight * ratio
                break
            total += s.weight
        self.project.progress = min(total, 1.0)
        self.project.current_stage = stage
        self._emit(stage, TaskStatus.RUNNING, ratio, message)

    def _emit(self, stage: str, status: TaskStatus, ratio: float, message: str | None) -> None:
        if self._on_event:
            self._on_event(TaskEvent(
                project_id=self.project.id,
                stage=stage,
                status=status,
                progress=ratio,
                message=message,
            ))


async def _placeholder_video(out_path: Path, duration: float) -> Path:
    """生成黑色占位视频。"""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s=1080x1920:d={duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    await _run_cmd(cmd)
    return out_path


async def _run_cmd(cmd: list[str]) -> None:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{stderr.decode()}")
