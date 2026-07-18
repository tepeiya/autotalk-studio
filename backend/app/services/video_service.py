"""Video Service - 最终视频合成（拼接 + 字幕 + BGM）。"""
from __future__ import annotations

import logging
from pathlib import Path

from ..core.storage import get_storage
from ..utils.ffmpeg_utils import concat_videos, mix_audio_video

logger = logging.getLogger(__name__)


class VideoService:
    """分镜视频 → 最终成片。"""

    async def compose(
        self,
        shot_videos: list[Path],
        bgm_path: Path | None = None,
        bgm_volume: float = 0.3,
        subtitle_srt: Path | None = None,
        output_path: Path | None = None,
    ) -> Path:
        storage = get_storage()
        out = output_path or storage.videos_dir / f"{storage.gen_id('video_')}.mp4"
        out.parent.mkdir(parents=True, exist_ok=True)

        if not shot_videos:
            raise ValueError("No shot videos to compose")

        # 1) 拼接
        concat_path = out.parent / f"{out.stem}_concat.mp4"
        await concat_videos(shot_videos, concat_path)

        # 2) 混 BGM（可选）
        if bgm_path:
            final = await mix_audio_video(
                video_path=concat_path,
                bgm_path=bgm_path,
                bgm_volume=bgm_volume,
                output_path=out,
            )
            concat_path.unlink(missing_ok=True)
            return final
        else:
            concat_path.rename(out)
            return out


video_service = VideoService()
