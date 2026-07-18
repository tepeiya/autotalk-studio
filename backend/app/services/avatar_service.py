"""Avatar Service - 数字人口播合成。"""
from __future__ import annotations

from pathlib import Path

from ..config import get_settings
from ..core.schemas import AvatarProfile
from ..core.storage import get_storage
from ..providers.base import registry


class AvatarService:
    """数字人形象注册 + 口播视频生成。"""

    async def register(
        self,
        portrait_path: Path,
        name: str,
        provider_name: str | None = None,
    ) -> AvatarProfile:
        settings = get_settings()
        pname = provider_name or settings.avatar.default_provider

        storage = get_storage()
        portrait = storage.avatars_dir / f"{name}_portrait{portrait_path.suffix}"
        portrait.write_bytes(portrait_path.read_bytes())

        provider = self._build(pname)
        try:
            internal_id = await provider.register_portrait(portrait, name)
        except NotImplementedError:
            internal_id = str(portrait)

        profile = AvatarProfile(
            id=storage.gen_id("avatar_"),
            name=name,
            provider=pname,
            portrait_path=str(portrait),
        )
        meta = storage.avatars_dir / f"{profile.id}.json"
        meta.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
        meta.with_suffix(".internal_id.txt").write_text(internal_id, encoding="utf-8")
        return profile

    def list_avatars(self) -> list[AvatarProfile]:
        storage = get_storage()
        result = []
        for p in storage.avatars_dir.glob("*.json"):
            try:
                result.append(AvatarProfile.model_validate_json(p.read_text(encoding="utf-8")))
            except Exception:
                continue
        return result

    async def render(
        self,
        audio_path: Path,
        avatar_id: str,
        output_path: Path | None = None,
        background_path: Path | None = None,
        provider_name: str | None = None,
    ) -> Path:
        settings = get_settings()
        pname = provider_name or settings.avatar.default_provider
        provider = self._build(pname)

        storage = get_storage()
        # 找到 avatar 的 portrait_path
        meta = storage.avatars_dir / f"{avatar_id}.json"
        if not meta.exists():
            raise FileNotFoundError(f"Avatar not found: {avatar_id}")
        profile = AvatarProfile.model_validate_json(meta.read_text(encoding="utf-8"))

        output = output_path or storage.tmp_dir / f"{storage.gen_id('avatar_')}.mp4"
        return await provider.render(
            audio_path=audio_path,
            portrait_path=Path(profile.portrait_path),
            output_path=output,
            background_path=background_path,
        )

    def _build(self, name: str):
        settings = get_settings()
        cfg = settings.avatar
        if name == "musetalk":
            return registry.create("avatar", "musetalk", base_url=cfg.musetalk_base_url)
        if name == "wav2lip":
            return registry.create("avatar", "wav2lip", base_url=cfg.wav2lip_base_url)
        if name == "heygem":
            return registry.create("avatar", "heygem", base_url=cfg.heygem_base_url)
        raise ValueError(f"Unknown avatar provider: {name}")


avatar_service = AvatarService()
