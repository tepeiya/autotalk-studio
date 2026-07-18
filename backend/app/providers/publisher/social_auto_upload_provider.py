"""Social-Auto-Upload Publisher - 接入 dreammis/social-auto-upload 真实多平台发布。

调用方式（自动检测优先级）：
1. `sau <platform> upload-video --account <account> --file <video> --title <title> --desc <desc>`
2. `python cli_main.py <platform> <account> upload <video> -pt 0`

前置条件：
- 用户已 clone social-auto-upload 项目到 SOCIAL_AUTO_UPLOAD_PATH（默认 /workspace/social-auto-upload）
- 已通过 `sau <platform> login --account <account>` 扫码登录获取 cookie
- 已 `playwright install chromium` 安装浏览器

支持平台（platform 映射）：
- douyin / bilibili / kuaishou / xiaohongshu / tencent / baijiahao / tiktok / youtube

未安装时会抛出清晰错误，便于上层展示给用户。
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any

from ..base import registry
from .base import BasePublisher

logger = logging.getLogger(__name__)

# 平台 → social-auto-upload 内部名映射
PLATFORM_MAP: dict[str, str] = {
    "douyin": "douyin",
    "bilibili": "bilibili",
    "kuaishou": "kuaishou",
    "xiaohongshu": "xiaohongshu",
    "xhs": "xiaohongshu",
    "tencent": "tencent",
    "weixin_video": "tencent",
    "baijiahao": "baijiahao",
    "tiktok": "tiktok",
    "youtube": "youtube",
}


@registry.register
class SocialAutoUploadPublisher(BasePublisher):
    """通过 social-auto-upload 子进程发布视频到真实社交平台。"""

    name = "social_auto_upload"

    def __init__(
        self,
        project_path: str | None = None,
        default_account: str = "default",
        chrome_path: str | None = None,
        headless: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        # 项目根路径：默认 /workspace/social-auto-upload
        self.project_path = Path(project_path) if project_path else Path("/workspace/social-auto-upload")
        self.default_account = default_account
        self.chrome_path = chrome_path or os.environ.get("LOCAL_CHROME_PATH")
        self.headless = headless

    async def publish(
        self,
        video_path: Path,
        title: str,
        description: str | None = None,
        tags: list[str] | None = None,
        cover_path: Path | None = None,
        platform: str = "douyin",
        account: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """发布视频。

        platform: AutoTalk 内部平台名（douyin/bilibili/...）
        account: social-auto-upload 中的账号名，对应 cookies/<plat>_uploader/<account>.json
        """
        sau_platform = PLATFORM_MAP.get(platform, platform)
        acc = account or self.default_account

        # 1) 校验项目路径
        if not self.project_path.exists():
            raise FileNotFoundError(
                f"social-auto-upload 项目不存在: {self.project_path}\n"
                f"请先 git clone https://github.com/dreammis/social-auto-upload 到该路径，"
                f"并按其 README 完成 `playwright install chromium` 和 `sau {sau_platform} login --account {acc}`"
            )

        # 2) 校验视频文件
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        # 3) 校验 cookie
        cookie_file = self.project_path / "cookies" / f"{sau_platform}_uploader" / f"{acc}.json"
        if not cookie_file.exists():
            raise FileNotFoundError(
                f"Cookie 不存在: {cookie_file}\n"
                f"请先扫码登录: cd {self.project_path} && sau {sau_platform} login --account {acc}"
            )

        # 4) 准备 meta txt 文件（social-auto-upload 旧版 CLI 要求同名 .txt 描述文件）
        # 格式：<title>\n#tag1 #tag2 #tag3
        tag_str = " ".join(f"#{t.replace(' ', '')}" for t in (tags or []))
        desc_body = f"{description}\n{tag_str}".strip() if description else tag_str
        meta_path = video_path.with_suffix(".txt")
        meta_path.write_text(f"{title}\n{desc_body}", encoding="utf-8")

        # 5) 选择 CLI 入口
        sau_cli = shutil.which("sau")
        env = os.environ.copy()
        if self.chrome_path:
            env["LOCAL_CHROME_PATH"] = self.chrome_path

        if sau_cli:
            # 新版 CLI: sau <platform> upload-video --account <acc> --file <video> --title <title> --desc <desc>
            cmd = [
                sau_cli, sau_platform, "upload-video",
                "--account", acc,
                "--file", str(video_path),
                "--title", title,
                "--desc", desc_body or title,
            ]
        else:
            # 旧版: python cli_main.py <platform> <account> upload <video> -pt 0
            cli_main = self.project_path / "cli_main.py"
            if not cli_main.exists():
                raise FileNotFoundError(
                    f"未找到 sau CLI 或 {cli_main}。\n"
                    f"请安装: pip install social-auto-upload 或在项目目录运行 `pip install -r requirements.txt`"
                )
            cmd = [
                "python3", str(cli_main),
                sau_platform, acc, "upload",
                str(video_path),
                "-pt", "0",
            ]

        logger.info("social-auto-upload cmd: %s (cwd=%s)", " ".join(cmd), self.project_path)

        # 6) 执行子进程
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self.project_path),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        out = stdout.decode(errors="replace") if stdout else ""
        err = stderr.decode(errors="replace") if stderr else ""

        if proc.returncode != 0:
            raise RuntimeError(
                f"social-auto-upload 发布失败 (exit={proc.returncode}):\n"
                f"STDOUT: {out[-1500:]}\n"
                f"STDERR: {err[-1500:]}"
            )

        logger.info("social-auto-upload success: %s", out[-500:])

        return {
            "platform": platform,
            "account": acc,
            "video_url": str(video_path),
            "title": title,
            "stdout_tail": out[-500:],
            "cookie_file": str(cookie_file),
        }

    async def health_check(self) -> bool:
        """检查 social-auto-upload 项目路径是否存在且能找到 sau CLI。"""
        if not self.project_path.exists():
            return False
        return shutil.which("sau") is not None or (self.project_path / "cli_main.py").exists()

    def get_config_schema(self) -> dict[str, Any]:
        return {
            "project_path": {
                "type": "string",
                "default": "/workspace/social-auto-upload",
                "description": "social-auto-upload 仓库根路径",
            },
            "default_account": {
                "type": "string",
                "default": "default",
                "description": "默认账号名（对应 cookies/<plat>_uploader/<account>.json）",
            },
            "chrome_path": {
                "type": "string",
                "description": "本地 Chrome 可执行文件路径（可选，解决 chromium 兼容性问题）",
            },
            "headless": {"type": "bool", "default": False},
            "cookie": {
                "type": "string",
                "description": "保留字段，用于 BasePublisher 兼容；实际 cookie 在 cookies/ 目录",
            },
            "platforms": {
                "type": "list",
                "options": list(PLATFORM_MAP.keys()),
                "description": "AutoTalk 平台名 → social-auto-upload 平台名自动映射",
            },
        }
