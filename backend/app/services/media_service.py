"""Media Service - BGM + 背景素材管理。"""
from __future__ import annotations

from pathlib import Path

from ..core.schemas import MediaItem
from ..core.storage import get_storage
from ..providers.base import registry
from ..providers.media.bgm_provider import BGMProvider
from ..providers.media.background_provider import BackgroundProvider


class MediaService:
    """BGM 与背景素材库服务。"""

    def __init__(self) -> None:
        self._bgm: BGMProvider | None = None
        self._bg: BackgroundProvider | None = None

    @property
    def bgm(self) -> BGMProvider:
        if self._bgm is None:
            self._bgm = registry.create("media", "bgm")
        return self._bgm

    @property
    def background(self) -> BackgroundProvider:
        if self._bg is None:
            self._bg = registry.create("media", "background")
        return self._bg

    def list_bgm(self) -> list[MediaItem]:
        return [
            MediaItem(id=it["id"], type="bgm", name=it["name"], path=it["path"], tags=it.get("tags", []))
            for it in self.bgm.list_bgm()
        ]

    def list_backgrounds(self) -> list[MediaItem]:
        return [
            MediaItem(id=it["id"], type="background", name=it["name"], path=it["path"], tags=it.get("tags", []))
            for it in self.background.list_backgrounds()
        ]

    def pick_bgm(self, mode: str = "random", bgm_id: str | None = None) -> Path | None:
        return self.bgm.pick(mode=mode, bgm_id=bgm_id)

    def pick_background(self, mode: str = "template", bg_id: str | None = None) -> Path | None:
        return self.background.pick(mode=mode, bg_id=bg_id)

    def upload_bgm(self, file_path: Path, name: str | None = None) -> MediaItem:
        storage = get_storage()
        name = name or file_path.stem
        target = storage.bgm_dir / f"{name}{file_path.suffix}"
        target.write_bytes(file_path.read_bytes())
        return MediaItem(id=target.stem, type="bgm", name=name, path=str(target))

    def upload_background(self, file_path: Path, name: str | None = None) -> MediaItem:
        storage = get_storage()
        name = name or file_path.stem
        target = storage.backgrounds_dir / f"{name}{file_path.suffix}"
        target.write_bytes(file_path.read_bytes())
        return MediaItem(id=target.stem, type="background", name=name, path=str(target))


media_service = MediaService()
