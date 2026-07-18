"""Voices API - 声音克隆与 TTS 合成。"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ...core.schemas import VoiceProfile, SynthesizeRequest
from ...core.storage import get_storage
from ...services.voice_service import voice_service

router = APIRouter(prefix="/voices", tags=["voices"])


@router.get("", response_model=list[VoiceProfile])
async def list_voices():
    return voice_service.list_voices()


@router.get("/providers/{provider}/presets")
async def list_provider_voices(provider: str):
    return await voice_service.list_provider_voices(provider_name=provider)


@router.post("/clone", response_model=VoiceProfile)
async def clone_voice(
    file: UploadFile = File(...),
    name: str = Form(...),
    provider: str | None = Form(None),
):
    sample_path = get_storage().tmp_dir / f"upload_{file.filename}"
    with open(sample_path, "wb") as f:
        f.write(await file.read())
    return await voice_service.clone(sample_path, name, provider_name=provider)


@router.post("/synthesize")
async def synthesize(req: SynthesizeRequest, provider: str | None = None):
    audio_path = await voice_service.synthesize(req, provider_name=provider)
    return {"audio_path": str(audio_path), "audio_url": f"/static/{Path(audio_path).name}"}
