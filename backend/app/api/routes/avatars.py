"""Avatars API - 数字人形象注册与渲染。"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ...core.schemas import AvatarProfile
from ...core.storage import get_storage
from ...services.avatar_service import avatar_service

router = APIRouter(prefix="/avatars", tags=["avatars"])


@router.get("", response_model=list[AvatarProfile])
async def list_avatars():
    return avatar_service.list_avatars()


@router.post("/register", response_model=AvatarProfile)
async def register_avatar(
    file: UploadFile = File(...),
    name: str = Form(...),
    provider: str | None = Form(None),
):
    portrait_path = get_storage().tmp_dir / f"upload_{file.filename}"
    with open(portrait_path, "wb") as f:
        f.write(await file.read())
    return await avatar_service.register(portrait_path, name, provider_name=provider)


@router.post("/render")
async def render_avatar(
    audio_path: str = Form(...),
    avatar_id: str = Form(...),
    provider: str | None = Form(None),
):
    out = await avatar_service.render(
        audio_path=Path(audio_path),
        avatar_id=avatar_id,
        provider_name=provider,
    )
    return {"video_path": str(out), "video_url": f"/static/{Path(out).name}"}
