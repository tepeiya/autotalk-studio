"""ffmpeg 工具函数。"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import ffmpeg

logger = logging.getLogger(__name__)


async def run_ffmpeg(stream: "ffmpeg.Stream") -> None:
    """异步执行 ffmpeg 命令。"""
    args = ffmpeg.compile(stream, overwrite_output=True)
    logger.info("ffmpeg: %s", " ".join(args))
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {stderr.decode()}")


async def concat_videos(video_paths: list[Path], output_path: Path) -> Path:
    """拼接多段视频。"""
    if len(video_paths) == 1:
        # 直接复制
        output_path.write_bytes(video_paths[0].read_bytes())
        return output_path

    # 用 concat demuxer 更高效
    list_file = output_path.parent / f"{output_path.stem}_concat.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in video_paths:
            f.write(f"file '{p.resolve()}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"concat failed: {stderr.decode()}")
    list_file.unlink(missing_ok=True)
    return output_path


async def mix_audio_video(
    video_path: Path,
    audio_path: Path | None = None,
    bgm_path: Path | None = None,
    bgm_volume: float = 0.3,
    output_path: Path | None = None,
) -> Path:
    """把音频/背景音乐混入视频。"""
    output_path = output_path or video_path.with_suffix(".mixed.mp4")
    inputs = [ffmpeg.input(str(video_path))]
    if audio_path:
        inputs.append(ffmpeg.input(str(audio_path)))
    if bgm_path:
        bgm_input = ffmpeg.input(str(bgm_path))
        inputs.append(bgm_input)

    # 简化：如果有 bgm 就混音，否则只替换或保留原音
    streams = [inputs[0].video]
    if len(inputs) > 1:
        mixed = inputs[1].audio
        if len(inputs) > 2:
            mixed = ffmpeg.filter([inputs[1].audio, inputs[2].audio.filter("volume", bgm_volume)], "amix")
        streams.append(mixed)
    else:
        streams.append(inputs[0].audio)

    stream = ffmpeg.output(*streams, str(output_path), vcodec="libx264", acodec="aac", shortest=True)
    await run_ffmpeg(stream)
    return output_path


async def get_duration(file_path: Path) -> float:
    """读取音视频时长。"""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(file_path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    try:
        return float(stdout.decode().strip())
    except ValueError:
        return 0.0
