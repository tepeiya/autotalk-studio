"""Reddit 业务线 Pipeline - 独立编排。

流程：collect → translate → (image / note / video) → publish_to_xiaohongshu

设计要点：
- 不修改现有 video Pipeline（app/core/pipeline.py）
- 复用现有 LLM/TTS/Avatar/Publisher provider
- 通过 RedditTaskManager 调度（独立于 video TaskManager）
- 通过回调推送 SSE 事件
"""
from __future__ import annotations

import asyncio
import logging
from typing import Callable

from ..providers.base import registry as preg
from ..core.schemas import (
    RedditHotPost,
    RedditImageArtifact,
    RedditNoteArtifact,
    RedditTask,
    RedditTaskCreate,
    RedditTaskEvent,
    RedditTaskStatus,
    TranslatedPost,
    RedditVideoArtifact,
    ScriptRequest,
)
from ..core.storage import get_storage

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[RedditTaskEvent], None]


class RedditPipeline:
    """Reddit 业务线 Pipeline。"""

    def __init__(self, task: RedditTask, on_event: ProgressCallback | None = None) -> None:
        self.task = task
        self._on_event = on_event
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def _emit(
        self,
        stage: str,
        status: RedditTaskStatus,
        progress: float,
        message: str | None = None,
        post_id: str | None = None,
    ) -> None:
        self.task.status = status
        self.task.current_stage = stage
        self.task.progress = progress
        ev = RedditTaskEvent(
            task_id=self.task.id,
            stage=stage,
            status=status,
            progress=progress,
            message=message,
            post_id=post_id,
        )
        if self._on_event:
            try:
                self._on_event(ev)
            except Exception:
                logger.exception("on_event callback failed")

    async def run(self) -> None:
        """执行完整 pipeline。"""
        params: RedditTaskCreate = self.task.params
        storage = get_storage()
        ws = storage.reddit_posts_dir / self.task.id
        ws.mkdir(parents=True, exist_ok=True)

        try:
            # ── Stage 1: 采集 ────────────────────────
            self._emit("collect", RedditTaskStatus.COLLECTING, 0.0, "开始采集 Reddit 热帖")
            collector = preg.create("collector", params.collector)
            raw_posts = await collector.collect(
                source=params.subreddit,
                limit=params.limit,
                time_filter=params.time_filter,
            )
            self.task.posts = [RedditHotPost(**p) for p in raw_posts]
            self._emit("collect", RedditTaskStatus.COLLECTING, 0.15,
                       f"采集到 {len(self.task.posts)} 篇热帖", None)

            # ── Stage 2: 翻译 ───────────────────────
            self._emit("translate", RedditTaskStatus.TRANSLATING, 0.15, "开始翻译润色")
            translator = preg.create("translator", params.translator)
            translated: list[TranslatedPost] = []
            for i, post in enumerate(self.task.posts):
                if self._cancelled:
                    self._emit("translate", RedditTaskStatus.CANCELLED, 0.15, "已取消")
                    return
                out = await translator.translate_and_polish(
                    title=post.title,
                    body=post.selftext or "",
                    target_lang="zh",
                )
                t = TranslatedPost(
                    post_id=post.post_id,
                    original_title=post.title,
                    original_text=post.selftext,
                    title_cn=out.get("title_cn", post.title),
                    summary_cn=out.get("summary_cn", ""),
                    body_cn=out.get("body_cn", post.selftext),
                    key_points=out.get("key_points", []),
                    tags=out.get("tags", []),
                )
                translated.append(t)
                # 持久化翻译结果
                (ws / f"{post.post_id}_translated.json").write_text(
                    t.model_dump_json(indent=2), encoding="utf-8"
                )
                progress = 0.15 + 0.25 * (i + 1) / len(self.task.posts)
                self._emit("translate", RedditTaskStatus.TRANSLATING, progress,
                           f"翻译完成 [{i + 1}/{len(self.task.posts)}]", post.post_id)
            self.task.translated = translated

            # ── Stage 3: 生成产物 ─────────────────────
            self._emit("generate", RedditTaskStatus.GENERATING, 0.40, "开始生成图片/笔记")
            n = max(1, len(translated))
            for i, t in enumerate(translated):
                if self._cancelled:
                    self._emit("generate", RedditTaskStatus.CANCELLED, 0.40, "已取消")
                    return

                # 图片
                if params.generate_image:
                    try:
                        image_provider = preg.create("image", params.image_provider)
                        img_path = storage.reddit_images_dir / self.task.id / f"{t.post_id}.png"
                        prompt = f"{t.title_cn}. {t.summary_cn}"
                        await image_provider.generate(
                            prompt=prompt,
                            output_path=img_path,
                            width=1080,
                            height=1080,
                        )
                        self.task.images.append(RedditImageArtifact(
                            post_id=t.post_id,
                            image_path=str(img_path),
                            url=f"/static/reddit/images/{self.task.id}/{t.post_id}.png",
                            prompt=prompt,
                        ))
                    except Exception as e:
                        logger.warning("Image gen failed for %s: %s", t.post_id, e)
                        self._emit("generate", RedditTaskStatus.GENERATING, 0.40,
                                   f"图片生成失败：{e}", t.post_id)

                # 笔记
                if params.generate_note:
                    try:
                        note_provider = preg.create("note", params.note_provider)
                        note_path = storage.reddit_notes_dir / self.task.id / f"{t.post_id}.md"
                        await note_provider.generate_note(
                            title=t.title_cn,
                            body=t.body_cn,
                            tags=t.tags,
                            output_path=note_path,
                        )
                        self.task.notes.append(RedditNoteArtifact(
                            post_id=t.post_id,
                            note_path=str(note_path),
                            url=f"/static/reddit/notes/{self.task.id}/{t.post_id}.md",
                            title=t.title_cn,
                            body=t.body_cn,
                            tags=t.tags,
                            image_paths=[str(a.image_path) for a in self.task.images
                                         if a.post_id == t.post_id],
                        ))
                    except Exception as e:
                        logger.warning("Note gen failed for %s: %s", t.post_id, e)
                        self._emit("generate", RedditTaskStatus.GENERATING, 0.40,
                                   f"笔记生成失败：{e}", t.post_id)

                # 视频（可选 - 复用 video pipeline 的 LLM+TTS+Avatar）
                if params.generate_video:
                    try:
                        video_path = await self._generate_video_for_post(t, ws)
                        self.task.videos.append(RedditVideoArtifact(
                            post_id=t.post_id,
                            video_path=str(video_path),
                            url=f"/static/reddit/videos/{self.task.id}/{t.post_id}.mp4",
                        ))
                    except Exception as e:
                        logger.warning("Video gen failed for %s: %s", t.post_id, e)
                        self._emit("generate", RedditTaskStatus.GENERATING, 0.40,
                                   f"视频生成失败：{e}", t.post_id)

                progress = 0.40 + 0.40 * (i + 1) / n
                self._emit("generate", RedditTaskStatus.GENERATING, progress,
                           f"产物生成完成 [{i + 1}/{n}]", t.post_id)

            # ── Stage 4: 发布到小红书 ─────────────────
            if params.publish_to_xiaohongshu:
                self._emit("publish", RedditTaskStatus.PUBLISHING, 0.85, "开始发布到小红书")
                try:
                    await self._publish_to_xiaohongshu(params.xiaohongshu_account)
                    self._emit("publish", RedditTaskStatus.PUBLISHING, 0.95, "发布完成")
                except FileNotFoundError as e:
                    logger.warning("Publish skipped: %s", e)
                    self._emit("publish", RedditTaskStatus.PUBLISHING, 0.85,
                               f"发布跳过：{e}")
                except Exception as e:
                    logger.exception("Publish failed")
                    self._emit("publish", RedditTaskStatus.PUBLISHING, 0.85,
                               f"发布失败：{e}")

            self._emit("done", RedditTaskStatus.SUCCESS, 1.0, "全部完成")

        except Exception as e:
            logger.exception("Reddit pipeline failed")
            self._emit("error", RedditTaskStatus.FAILED, self.task.progress,
                       f"Pipeline 失败：{e}")

    async def _generate_video_for_post(self, t: TranslatedPost, ws) -> "Path":
        """复用现有 video pipeline 生成视频（mock 默认）。"""
        # 简化版：直接调 mock LLM + mock TTS + mock Avatar + ffmpeg concat
        # 这里只做最小化路径，完整版可调 video_service
        from ..core.schemas import ScriptRequest
        from ..services.script_service import script_service
        from ..services.voice_service import voice_service
        from ..services.avatar_service import avatar_service
        from ..utils.ffmpeg_utils import concat_videos

        storage = get_storage()
        shot_ws = storage.reddit_videos_dir / self.task.id
        shot_ws.mkdir(parents=True, exist_ok=True)

        # 用翻译后内容生成 1 分镜"脚本"
        req = ScriptRequest(
            topic=t.title_cn + " " + t.summary_cn,
            style="informative",
            duration_sec=15,
            language="zh",
        )
        script = await script_service.generate(req, llm_provider="mock")

        # TTS
        audio_path = shot_ws / f"{t.post_id}.wav"
        await voice_service.synthesize(
            text=script.full_text,
            voice_id="mock_male",
            output_path=audio_path,
            tts_provider="mock",
        )

        # Avatar
        video_path = shot_ws / f"{t.post_id}.mp4"
        # 找一个已注册的 avatar_id，没有就传 None 让 mock 自己处理
        try:
            avatars = avatar_service.list_avatars()
            avatar_id = avatars[0].id if avatars else None
        except Exception:
            avatar_id = None
        await avatar_service.render(
            audio_path=audio_path,
            avatar_id=avatar_id,
            output_path=video_path,
            avatar_provider="mock",
        )
        return video_path

    async def _publish_to_xiaohongshu(self, account: str) -> None:
        """调用 social_auto_upload publisher 发布笔记/图片到小红书。"""
        from ..providers.publisher.social_auto_upload_provider import PLATFORM_MAP
        import os

        sau_path = os.environ.get("SOCIAL_AUTO_UPLOAD_PATH", "/workspace/social-auto-upload")
        publisher = preg.create_fresh(
            "publisher", "social_auto_upload",
            project_path=sau_path,
            default_account=account,
        )

        for note in self.task.notes:
            # 找该笔记关联的图片
            img_paths = [Path(p) for p in note.image_paths if Path(p).exists()]
            # 取第一张图作为视频/图片上传（小红书支持图文笔记）
            if img_paths:
                await publisher.publish(
                    video_path=img_paths[0],
                    title=note.title,
                    description=note.body,
                    tags=note.tags,
                    platform="xiaohongshu",
                    account=account,
                )
            # 如有视频也发布
            for v in self.task.videos:
                if v.post_id == note.post_id:
                    await publisher.publish(
                        video_path=Path(v.video_path),
                        title=note.title,
                        description=note.body,
                        tags=note.tags,
                        platform="xiaohongshu",
                        account=account,
                    )


# 延迟导入 Path（避免顶层循环）
from pathlib import Path  # noqa: E402
