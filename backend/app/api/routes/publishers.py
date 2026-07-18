"""Publishers API - 多平台发布接口。"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Form, HTTPException
from pydantic import BaseModel

from ...config import get_settings
from ...core.storage import get_storage
from ...providers.base import registry as preg
from ...providers.publisher.social_auto_upload_provider import PLATFORM_MAP

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/publishers", tags=["publishers"])

# social-auto-upload 默认路径
def _sau_project_path() -> Path:
    """从配置或环境变量获取 social-auto-upload 项目路径。"""
    env_path = os.environ.get("SOCIAL_AUTO_UPLOAD_PATH")
    if env_path:
        return Path(env_path)
    return Path("/workspace/social-auto-upload")


class PublishResponse(BaseModel):
    platform: str
    video_url: str
    title: str
    tags: list[str] = []
    description: str | None = None
    account: str | None = None
    stdout_tail: str | None = None


@router.get("/platforms")
async def list_platforms():
    """返回所有已注册的 publisher provider 及其支持的配置 schema。"""
    items = preg.list_providers(type_filter="publisher")
    result = []
    for it in items:
        try:
            cls = preg.get_class("publisher", it["name"])
            instance = cls()
            schema = instance.get_config_schema()
            healthy = await instance.health_check()
        except Exception as e:
            logger.warning("health check failed for %s: %s", it["name"], e)
            schema = {}
            healthy = False
        result.append({
            "name": it["name"],
            "requires_gpu": it.get("requires_gpu", False),
            "class": it.get("class", it["name"]),
            "healthy": healthy,
            "config_schema": schema,
        })
    return result


@router.get("/supported-platforms")
async def list_supported_social_platforms():
    """列出 AutoTalk 支持的真实社交平台（用于 social_auto_upload provider）。"""
    sau_path = _sau_project_path()
    sau_installed = sau_path.exists() and (
        shutil.which("sau") is not None or (sau_path / "cli_main.py").exists()
    )
    return {
        "sau_installed": sau_installed,
        "sau_project_path": str(sau_path),
        "platforms": [
            {"name": k, "sau_name": v, "display": k}
            for k, v in PLATFORM_MAP.items()
        ],
    }


@router.get("/cookies")
async def list_cookies():
    """列出各平台 cookie 状态（cookies/<platform>_uploader/<account>.json）。"""
    sau_path = _sau_project_path()
    cookies_dir = sau_path / "cookies"
    if not cookies_dir.exists():
        return {"sau_path": str(sau_path), "cookies": [], "hint": "social-auto-upload 未安装或未登录"}
    items = []
    for sub in sorted(cookies_dir.iterdir()):
        if not sub.is_dir():
            continue
        platform = sub.name.replace("_uploader", "")
        for f in sorted(sub.glob("*.json")):
            stat = f.stat()
            items.append({
                "platform": platform,
                "account": f.stem,
                "path": str(f),
                "size_bytes": stat.st_size,
                "modified_at": stat.st_mtime,
            })
    return {"sau_path": str(sau_path), "cookies": items}


@router.post("/login")
async def trigger_login(
    platform: str = Form(...),
    account: str = Form("default"),
):
    """触发扫码登录（启动 social-auto-upload 的 login 子进程）。

    注意：此操作会启动 playwright 浏览器，需要本地有显示器或 Xvfb。
    在沙箱环境可能无法直接扫码，建议用户在本地终端手动执行登录命令。
    """
    sau_path = _sau_project_path()
    if not sau_path.exists():
        raise HTTPException(404, f"social-auto-upload 未安装: {sau_path}")

    sau_platform = PLATFORM_MAP.get(platform, platform)
    sau_cli = shutil.which("sau")
    if sau_cli:
        cmd = [sau_cli, sau_platform, "login", "--account", account]
    else:
        cli_main = sau_path / "cli_main.py"
        if not cli_main.exists():
            raise HTTPException(404, "未找到 sau CLI 或 cli_main.py")
        cmd = ["python3", str(cli_main), sau_platform, account, "login"]

    # 启动子进程（不阻塞请求，5 秒后返回提示）
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(sau_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except Exception as e:
        raise HTTPException(500, f"启动登录失败: {e}")

    # 给浏览器 5 秒启动时间
    await asyncio.sleep(5)
    if proc.returncode is not None:
        # 进程已结束（可能扫码完成或失败）
        stdout, stderr = await proc.communicate()
        return {
            "platform": platform,
            "account": account,
            "status": "finished",
            "stdout": stdout.decode(errors="replace")[-500:] if stdout else "",
            "stderr": stderr.decode(errors="replace")[-500:] if stderr else "",
        }

    return {
        "platform": platform,
        "account": account,
        "status": "browser_started",
        "pid": proc.pid,
        "hint": "浏览器已启动，请在浏览器中扫码完成登录。登录完成后 cookie 会自动保存。",
        "cmd": " ".join(cmd),
    }


@router.get("/videos")
async def list_generated_videos():
    """列出所有已生成的最终视频（storage/videos/*.mp4）。"""
    videos_dir = get_storage().videos_dir
    if not videos_dir.exists():
        return []
    items = []
    for p in sorted(videos_dir.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
        stat = p.stat()
        items.append({
            "id": p.stem,
            "filename": p.name,
            "path": str(p),
            "url": f"/static/videos/{p.name}",
            "size_bytes": stat.st_size,
            "modified_at": stat.st_mtime,
        })
    return items


@router.get("/published")
async def list_published():
    """列出所有已发布的视频记录（storage/published/）。"""
    pub_dir = get_storage().root / "published"
    if not pub_dir.exists():
        return []
    items = []
    for p in sorted(pub_dir.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
        stat = p.stat()
        items.append({
            "id": p.stem,
            "filename": p.name,
            "path": str(p),
            "url": f"/static/published/{p.name}",
            "size_bytes": stat.st_size,
            "modified_at": stat.st_mtime,
            "platform": "local",
        })
    return items


@router.post("/publish", response_model=PublishResponse)
async def publish(
    video_path: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    tags: str = Form(""),
    platform: str = Form("dummy"),
    account: str = Form("default"),
):
    """把视频发布到指定平台。

    platform:
        - dummy / social_auto_upload（publisher provider 名）
        - 当 platform=douyin/bilibili/... 时，自动用 social_auto_upload provider 发布到对应社交平台
    """
    p = Path(video_path)
    if not p.is_absolute():
        p = get_storage().resolve(p)
    if not p.exists():
        raise HTTPException(404, f"Video not found: {video_path}")

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    # 路由：social_auto_upload provider 支持把社交平台名作为 platform 传入
    # 1) platform == "dummy" → dummy publisher
    # 2) platform == "social_auto_upload" → 默认发布到 douyin
    # 3) platform in {douyin/bilibili/...} → social_auto_upload.publish(platform=...)
    if platform == "dummy":
        provider_name = "dummy"
        publish_kwargs: dict[str, Any] = {}
    elif platform in PLATFORM_MAP or platform == "social_auto_upload":
        provider_name = "social_auto_upload"
        publish_kwargs = {
            "platform": "douyin" if platform == "social_auto_upload" else platform,
            "account": account,
        }
    else:
        try:
            preg.get_class("publisher", platform)
            provider_name = platform
            publish_kwargs = {}
        except KeyError:
            raise HTTPException(400, f"Unknown publisher/platform: {platform}")

    try:
        # 构造 publisher 实例时传入 social_auto_upload 的项目路径
        if provider_name == "social_auto_upload":
            sau_path = os.environ.get("SOCIAL_AUTO_UPLOAD_PATH", "/workspace/social-auto-upload")
            publisher = preg.create_fresh(
                "publisher", "social_auto_upload",
                project_path=sau_path,
                default_account=account,
            )
        else:
            publisher = preg.create("publisher", provider_name)
    except KeyError:
        raise HTTPException(400, f"Unknown publisher: {provider_name}")

    try:
        result = await publisher.publish(
            video_path=p,
            title=title,
            description=description or None,
            tags=tag_list,
            **publish_kwargs,
        )
    except FileNotFoundError as e:
        raise HTTPException(409, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))

    return PublishResponse(
        platform=str(result.get("platform", platform)),
        video_url=str(result.get("video_url", "")),
        title=title,
        tags=tag_list,
        description=description or None,
        account=result.get("account"),
        stdout_tail=result.get("stdout_tail"),
    )
