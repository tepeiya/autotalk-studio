"""Media API - BGM/背景素材管理。"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from ...core.schemas import MediaItem
from ...core.storage import get_storage
from ...services.media_service import media_service

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/bgm", response_model=list[MediaItem])
async def list_bgm():
    return media_service.list_bgm()


@router.get("/backgrounds", response_model=list[MediaItem])
async def list_backgrounds():
    return media_service.list_backgrounds()


@router.post("/bgm/upload", response_model=MediaItem)
async def upload_bgm(file: UploadFile = File(...), name: str | None = Form(None)):
    tmp = get_storage().tmp_dir / f"upload_{file.filename}"
    with open(tmp, "wb") as f:
        f.write(await file.read())
    return media_service.upload_bgm(tmp, name)


@router.post("/backgrounds/upload", response_model=MediaItem)
async def upload_background(file: UploadFile = File(...), name: str | None = Form(None)):
    tmp = get_storage().tmp_dir / f"upload_{file.filename}"
    with open(tmp, "wb") as f:
        f.write(await file.read())
    return media_service.upload_background(tmp, name)
