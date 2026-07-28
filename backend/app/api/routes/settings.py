"""Settings API - 读取和更新运行时配置（持久化到 config/config.yaml）。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field

from ...config import get_settings, reload_settings


router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsPatch(BaseModel):
    """Partial update payload. All fields optional; only supplied keys are merged."""

    host: str | None = None
    port: int | None = None
    cors_origins: str | None = None
    storage_root: str | None = None
    llm: dict[str, Any] | None = Field(default=None, description="LLM config override")
    tts: dict[str, Any] | None = Field(default=None, description="TTS config override")
    avatar: dict[str, Any] | None = Field(default=None, description="Avatar config override")
    media: dict[str, Any] | None = Field(default=None, description="Media config override")
    publisher: dict[str, Any] | None = Field(default=None, description="Publisher config override")
    pipeline: dict[str, Any] | None = Field(default=None, description="Pipeline config override")


class SettingsResponse(BaseModel):
    """Full settings snapshot, excluding sensitive values from being echoed if desired."""

    host: str
    port: int
    cors_origins: str
    storage_root: str
    llm: dict[str, Any]
    tts: dict[str, Any]
    avatar: dict[str, Any]
    media: dict[str, Any]
    publisher: dict[str, Any]
    pipeline: dict[str, Any]
    yaml_path: str


def _expose_masked() -> SettingsResponse:
    """Return current settings as a plain dict (no secret masking by default)."""
    s = get_settings()
    data = s.to_yaml_dict()
    return SettingsResponse(yaml_path=str(s.yaml_path()), **data)


@router.get("", response_model=SettingsResponse)
async def get_settings_api() -> SettingsResponse:
    """Return the currently active settings snapshot."""
    return _expose_masked()


@router.patch("", response_model=SettingsResponse)
async def update_settings_api(
    patch: SettingsPatch = Body(...),
) -> SettingsResponse:
    """Partially update settings and persist to config/config.yaml.

    Environment variables still take precedence over YAML values (per Pydantic Settings).
    """
    current = get_settings()

    # Build a plain-dict patch from only the provided fields
    raw_patch: dict[str, Any] = {}
    for field, value in patch.model_dump(exclude_unset=True).items():
        if value is None:
            continue
        if field in ("host", "port", "cors_origins", "storage_root"):
            raw_patch[field] = value
        elif field in ("llm", "tts", "avatar", "media", "publisher", "pipeline"):
            if isinstance(value, dict) and value:
                raw_patch[field] = value

    if not raw_patch:
        raise HTTPException(status_code=400, detail="No valid fields provided in patch")

    try:
        merged = current.apply_patch(raw_patch)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid patch: {e}") from e

    reload_settings(merged)
    return _expose_masked()
