"""Publishers API - 多平台发布占位接口。"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Form

from ...providers.base import registry as preg

router = APIRouter(prefix="/publishers", tags=["publishers"])


@router.post("/publish")
async def publish(
    video_path: str = Form(...),
    title: str = Form(...),
    platform: str = Form("dummy"),
):
    publisher = preg.create("publisher", platform)
    result = await publisher.publish(video_path=Path(video_path), title=title)
    return result
