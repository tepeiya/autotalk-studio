"""Image Generator Provider 实现。

- MockImageProvider: 用 PIL 生成纯色 + 文字图片，无任何外部依赖
- SdxlImageProvider: 预留接口，调用本地 SDXL WebUI 或 ComfyUI API（默认未启用）

为支持真实图片生成，可后续扩展：
- sdxl_provider (ComfyUI API)
- dalle_provider (OpenAI DALL-E 3)
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from ..base import registry
from .base import BaseImageProvider

logger = logging.getLogger(__name__)


def _has_pil() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


@registry.register
class MockImageProvider(BaseImageProvider):
    """用 PIL 生成纯色 + 文字标题图片。无 PIL 时降级到最小 PNG。"""

    name = "mock"

    # 一组配色（小红书风格暖色调）
    PALETTES = [
        ((255, 235, 200), (102, 51, 0)),  # 米黄/棕
        ((200, 230, 255), (0, 51, 102)),  # 浅蓝/深蓝
        ((255, 200, 220), (102, 0, 51)),  # 粉/暗红
        ((230, 255, 200), (51, 102, 0)),  # 浅绿/深绿
        ((240, 220, 255), (76, 0, 153)),  # 浅紫/深紫
    ]

    async def generate(
        self,
        prompt: str,
        output_path: Path,
        width: int = 1080,
        height: int = 1080,
        **kwargs: Any,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # 选择配色基于 prompt 哈希
        idx = abs(hash(prompt)) % len(self.PALETTES)
        bg, fg = self.PALETTES[idx]

        await asyncio.to_thread(self._render, prompt, output_path, width, height, bg, fg)
        logger.info("Mock image generated: %s", output_path)
        return output_path

    def _render(self, prompt: str, path: Path, w: int, h: int, bg, fg) -> None:
        if _has_pil():
            from PIL import Image, ImageDraw, ImageFont

            img = Image.new("RGB", (w, h), bg)
            draw = ImageDraw.Draw(img)
            # 标题（取 prompt 前 30 字，分多行）
            text = prompt[:60]
            # 选字号
            font = None
            for size in (72, 56, 48, 36):
                try:
                    font = ImageFont.truetype(
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size
                    )
                    break
                except Exception:
                    continue
            if font is None:
                font = ImageFont.load_default()

            # 简单换行：每行最多 18 字符
            lines = [text[i:i + 18] for i in range(0, len(text), 18)]
            line_h = h // (len(lines) + 4)
            y = h // 2 - (line_h * len(lines)) // 2
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                tw = bbox[2] - bbox[0]
                draw.text(((w - tw) // 2, y), line, fill=fg, font=font)
                y += line_h

            # 底部小字水印
            try:
                small_font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24
                )
            except Exception:
                small_font = font
            watermark = "AutoTalk Studio"
            bbox = draw.textbbox((0, 0), watermark, font=small_font)
            draw.text((w - (bbox[2] - bbox[0]) - 30, h - 50), watermark,
                      fill=fg, font=small_font)
            img.save(str(path), "PNG")
        else:
            # 极小占位 PNG（1x1 像素）
            import base64
            path.write_bytes(base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
            ))

    async def health_check(self) -> bool:
        return True


@registry.register
class SdxlImageProvider(BaseImageProvider):
    """SDXL ComfyUI API 预留接口 - 暂未实现真实调用，仅占位。"""

    name = "sdxl"
    requires_gpu = True

    def __init__(self, base_url: str = "http://127.0.0.1:8188", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.base_url = base_url

    async def generate(
        self,
        prompt: str,
        output_path: Path,
        width: int = 1080,
        height: int = 1080,
        **kwargs: Any,
    ) -> Path:
        raise NotImplementedError(
            "SDXL provider 尚未实现，请用 mock provider 或安装 ComfyUI 后扩展本 provider"
        )

    async def health_check(self) -> bool:
        return False
